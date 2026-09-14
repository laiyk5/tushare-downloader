"""Structured reports and presentation-only progress, independent of data writes."""

import json
import logging
import os
import re
import shutil
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import click
from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text


def terminal_text(value):
    """Remove terminal controls from source text without interpreting Rich markup."""
    value = re.sub(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)", "", str(value))
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    return "".join(c for c in value if c == "\n" or (ord(c) >= 32 and not 127 <= ord(c) <= 159))


def rich_terminal(settings):
    return (
        not settings.plain
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM") != "dumb"
        and sys.stdout.isatty()
        and sys.stderr.isatty()
    )


@dataclass(frozen=True)
class RangeDetail:
    start: date | None
    end: date | None
    reason: str
    count: int = 1

    def text(self):
        scope = (
            "Full snapshot"
            if self.start is None
            else str(self.start)
            if self.start == self.end
            else f"{self.start}..{self.end}"
        )
        return f"{scope} | {self.reason} | {self.count} blocks"


def merge_ranges(items):
    """Only adjacent ranges with the exact same reason may be combined."""
    merged = []
    for item in sorted(items, key=lambda x: (x.start or date.min, x.end or date.min, x.reason)):
        if (
            merged
            and item.start is not None
            and merged[-1].end is not None
            and item.reason == merged[-1].reason
            and (item.start - merged[-1].end) == timedelta(days=1)
        ):
            previous = merged[-1]
            merged[-1] = RangeDetail(
                previous.start, item.end, item.reason, previous.count + item.count
            )
        else:
            merged.append(item)
    return merged


def detail(api, block, reason):
    return RangeDetail(
        block.requested_start if api.query_kind == "time-range" else None,
        block.requested_end if api.query_kind == "time-range" else None,
        reason,
    )


class JsonFiles(logging.Handler):
    def __init__(self, path, limit=10 * 1024 * 1024):
        super().__init__()
        self.path, self.limit, self.part = path, limit, 0
        self.stream = path.open("x", encoding="utf-8")
        self.seconds = 0.0

    def emit(self, record):
        started = time.monotonic()
        try:
            line = (
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "level": record.levelname,
                        **record.payload,
                    },
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )
            if self.stream.tell() and self.stream.tell() + len(line.encode()) > self.limit:
                self.stream.close()
                self.part += 1
                self.stream = self.path.with_suffix(f".{self.part}.jsonl").open(
                    "x", encoding="utf-8"
                )
            self.stream.write(line)
            self.stream.flush()
        finally:
            self.seconds += time.monotonic() - started

    def close(self):
        self.stream.close()
        super().close()


class DetailedProgress(Progress):
    def get_renderables(self):
        yield self.make_tasks_table(self.tasks)
        if self.tasks:
            yield Text(self.tasks[0].fields.get("detail", ""), overflow="fold")
            recent = self.tasks[0].fields.get("recent", ())
            if recent:
                yield Panel(Text("\n".join(recent)), title="Recent activity", border_style="dim")


class Reporter:
    def __init__(self, settings, api, command, *, quiet=False, verbose=0, clock=time.monotonic):
        self.settings, self.api, self.command = settings, api, command
        self.quiet, self.verbose, self.clock = quiet, verbose, clock
        ident = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        self.folder = settings.report_dir / ident
        self.folder.mkdir(parents=True)
        self.log_path = settings.log_dir / f"{ident}.jsonl"
        self.handler = JsonFiles(self.log_path)
        self.logger = logging.Logger(ident, logging.DEBUG)
        self.logger.addHandler(self.handler)
        self.start = clock()
        self.last_progress = self.start
        self.report_seconds = 0.0
        self.io_failed = False
        self.progress = self.task = self.worker = None
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        self.output_error = None
        self.total = self.done = self.rows = self.attempts = self.failed = self.empty = (
            self.received
        ) = 0
        self.stage = "Preparing"
        self.scope = ""
        self.slice_started = self.start
        self.samples = deque(maxlen=20)
        self.recent = deque(maxlen=settings.terminal_log_lines)
        self.initial_plan = None
        self.event("invocation_started", api=api.name, command=command)
        if not self.io_failed:
            click.echo(f"Log: {self.log_path}")
        (self.folder / ".write-check").write_text("", encoding="utf-8")
        (self.folder / ".write-check").unlink()

    def event(self, event, level=logging.INFO, **fields):
        if not self.quiet and (level >= logging.INFO or self.verbose):
            message = terminal_text(
                f"{logging.getLevelName(level)} {event} "
                + " · ".join(f"{k}={v}" for k, v in fields.items())
            )
            with self.lock:
                self.recent.append(message)
        if level == logging.DEBUG and self.settings.log_level != "DEBUG":
            return
        if self.io_failed:
            return
        try:
            self.logger.log(
                level, event, extra={"payload": {"event": event, "api": self.api.name, **fields}}
            )
        except OSError:
            self.output_failure()

    def output_failure(self):
        self.io_failed = True
        try:
            click.echo(
                "Logging failed: log is incomplete; confirmed commits are retained. Execution will fail.",
                err=True,
            )
        except OSError:
            pass

    def report(self, name, heading, lines, *, explicit=False, sections=None):
        """Atomically replace one report, retaining the immutable original plan."""
        started = self.clock()
        path = self.folder / "report.md"
        temporary = path.with_suffix(".tmp")
        lines = tuple(lines)
        sections = (
            None if sections is None else tuple((title, tuple(items)) for title, items in sections)
        )
        if name == "before" and self.initial_plan is None:
            self.initial_plan = (lines, sections)

        def safe(value):
            return (
                str(value)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("|", "&#124;")
                .replace("\n", "<br>")
                .replace("\r", "")
            )

        def summary(stream, values):
            stream.write("| Item | Value |\n| --- | --- |\n")
            for value in values:
                key, separator, content = value.replace(": ", ":", 1).partition(":")
                stream.write(f"| {safe(key)} | {safe(content) if separator else '—'} |\n")
            stream.write("\n")

        def details(stream, groups):
            for title, items in groups or ():
                if not items:
                    continue
                stream.write(f"### {safe(title)} ({sum(i.count for i in items)} blocks)\n\n")
                stream.write("| Scope | Reason | Blocks |\n| --- | --- | ---: |\n")
                for item in items:
                    scope = (
                        "Full snapshot"
                        if item.start is None
                        else (
                            str(item.start)
                            if item.start == item.end
                            else f"{item.start}..{item.end}"
                        )
                    )
                    stream.write(f"| {safe(scope)} | {safe(item.reason)} | {item.count} |\n")
                stream.write("\n")

        try:
            with temporary.open("w", encoding="utf-8") as stream:
                stream.write(f"# {safe(heading)}\n\n")
                stream.write(f"API: {self.api.name} · Command: {self.command}\n\n")
                if name == "before":
                    stream.write("Final result: not recorded\n\n")
                    stream.write(
                        "This is a plan, not evidence that no data has been committed.\n\n"
                    )
                summary(stream, lines)
                if name != "before":
                    stream.write("## Results and attention\n\n")
                    details(stream, sections)
                    if self.initial_plan is not None:
                        stream.write("## Original plan\n\n")
                        summary(stream, self.initial_plan[0])
                        details(stream, self.initial_plan[1])
                else:
                    details(stream, sections)
                stream.write("## Logs\n\n")
                for part in range(self.handler.part + 1):
                    log = (
                        self.log_path if part == 0 else self.log_path.with_suffix(f".{part}.jsonl")
                    )
                    stream.write(f"- {safe(log)}\n")
            temporary.replace(path)
            self.show_report(name, heading, lines, sections, explicit)
            click.echo(f"Report: {path}")
            return path
        finally:
            self.report_seconds += self.clock() - started

    def show_report(self, name, heading, lines, sections, explicit):
        if self.quiet and not explicit:
            if name != "before" and lines:
                click.echo(terminal_text(lines[0]))
            return
        displayed = lines if sections is not None else lines[: self.settings.report_max_items]
        rich = rich_terminal(self.settings)
        console = Console(markup=False, highlight=False) if rich else None
        if rich:
            table = Table.grid(padding=(0, 2), expand=True)
            table.add_column(style="dim", ratio=1)
            table.add_column(ratio=3)
            for line in displayed:
                key, separator, value = terminal_text(line).partition(":")
                table.add_row(Text(key), Text(value.strip() if separator else ""))
            style = (
                "cyan"
                if name == "before"
                else (
                    "yellow"
                    if any(
                        word in " ".join(lines).lower()
                        for word in ["failed", "unknown", "interrupted", "unverified"]
                    )
                    else "green"
                )
            )
            console.print(Panel(table, title=Text(heading), border_style=style))
        else:
            click.echo(terminal_text(heading))
            for line in displayed:
                click.echo(terminal_text(line))
        if len(displayed) < len(lines):
            click.echo(f"{len(lines) - len(displayed)} more items; see the full report.")
        for title, items in sections or ():
            if not items:
                continue
            grouped = merge_ranges(items)
            heading = f"{title} ({sum(i.count for i in items)} blocks)"
            texts = [
                terminal_text(item.text()) for item in grouped[: self.settings.report_max_items]
            ]
            omitted = len(grouped) - self.settings.report_max_items
            if omitted > 0:
                texts.append(f"{omitted} more ranges; see the full report.")
            if rich:
                console.print(
                    Panel(
                        Group(*(Text(text) for text in texts)),
                        title=Text(heading),
                        border_style="dim",
                    )
                )
            else:
                click.echo("\n" + terminal_text(heading))
                for text in texts:
                    if shutil.get_terminal_size((80, 24)).columns < 65:
                        text = text.replace(" | ", "\n  ")
                    click.echo("  " + text)

    def begin(self, total):
        self.total = total
        if not total or self.quiet or self.settings.progress == "off":
            return
        if rich_terminal(self.settings):
            narrow = shutil.get_terminal_size((80, 24)).columns < 80
            columns = [
                TextColumn("{task.description}"),
                TextColumn("{task.completed}/{task.total}"),
            ]
            if not narrow:
                columns += [BarColumn(), TimeElapsedColumn()]
            self.progress = DetailedProgress(
                *columns, console=Console(stderr=True), auto_refresh=False
            )
            self.task = self.progress.add_task("Downloading", total=total, detail="ETA unavailable")
            self.progress.start()
        self.worker = threading.Thread(target=self._tick, name="downloader-progress", daemon=True)
        self.worker.start()

    def _tick(self):
        while not self.stop_event.wait(0.25):
            try:
                self.render_progress()
            except (OSError, ValueError) as error:
                self.output_error = type(error).__name__
                return

    def phase(self, stage):
        with self.lock:
            changed = stage != self.stage
            self.stage = stage
        if changed and not self.quiet and (self.settings.progress == "off" or self.verbose):
            click.echo(terminal_text(f"Phase: {stage}"), err=True)

    def begin_slice(self, scope):
        with self.lock:
            self.scope = scope
            self.slice_started = self.clock()
            self.stage = "Preparing request"

    def attempt(self):
        with self.lock:
            self.attempts += 1

    def receive(self, count):
        with self.lock:
            self.received += count
            self.stage = "Received/staged"

    def snapshot(self):
        with self.lock:
            elapsed = max(self.clock() - self.start, 0.001)
            eta = None
            # Use recent complete logical slices, including all waits and failed attempts.
            if (
                len(self.samples) >= 5
                and sum(self.samples) >= 10
                and self.stage not in {"Retry waiting", "Committing", "Stopped"}
            ):
                average = sum(self.samples) / len(self.samples)
                current = max(0, self.clock() - self.slice_started)
                if current <= average * 3:
                    eta = max(0, (self.total - self.done) * average - current)
            return {
                "done": self.done,
                "total": self.total,
                "elapsed": elapsed,
                "failed": self.failed,
                "empty": self.empty,
                "received": self.received,
                "rows": self.rows,
                "attempts": self.attempts,
                "stage": self.stage,
                "scope": self.scope,
                "eta": eta,
                "http_rate": self.attempts / elapsed,
                "row_rate": self.rows / elapsed,
            }

    def render_progress(self, *, final=False):
        if self.quiet or self.settings.progress == "off":
            return
        state = self.snapshot()
        eta = f"~{state['eta']:.0f}s" if state["eta"] is not None else "unavailable"
        text = (
            f"{state['stage']} {state['scope']}; Failed {state['failed']} empty {state['empty']}; "
            f"Received/staged {state['received']} rows; Committed input: {state['rows']} rows; "
            f"HTTP {state['http_rate']:.2f}/s; Written: {state['row_rate']:.1f} rows/s; ETA {eta}"
        )
        with self.lock:
            if self.progress:
                self.progress.update(
                    self.task,
                    completed=state["done"],
                    detail=terminal_text(text),
                    recent=tuple(self.recent),
                )
                self.progress.refresh()
            elif final or self.clock() - self.last_progress >= self.settings.progress_interval:
                click.echo(
                    f"Progress: {state['done']}/{state['total']}; Elapsed: {state['elapsed']:.1f}s; {text}",
                    err=True,
                )
                self.last_progress = self.clock()

    def advance(self, done, total, rows, attempts, failed, empty=0, *, stopped=False):
        with self.lock:
            self.samples.append(max(0, self.clock() - self.slice_started))
            self.done, self.total, self.rows = done, total, rows
            self.attempts, self.failed, self.empty = attempts, failed, empty
            self.stage = "Stopped" if stopped else "Block finished"
            self.slice_started = self.clock()
        self.render_progress(final=done == total)

    def stop_progress(self):
        self.stop_event.set()
        if self.worker:
            self.worker.join()
            self.worker = None
        if self.progress:
            self.progress.stop()
            self.progress = None
        if self.output_error:
            self.event("progress_unavailable", level=logging.WARNING, category=self.output_error)
            self.output_error = None

    def __enter__(self):
        return self

    def __exit__(self, error_type, error, traceback):
        try:
            if error_type is not None and not (self.folder / "report.md").exists():
                self.report(
                    "after",
                    "Preparation failed",
                    [
                        "Result: preparation failed; no data requests started",
                        f"Error category: {error_type.__name__}",
                    ],
                    explicit=True,
                )
        except OSError:
            self.output_failure()
        finally:
            self.close()

    def close(self):
        self.stop_progress()
        try:
            self.handler.close()
        except OSError:
            self.output_failure()
