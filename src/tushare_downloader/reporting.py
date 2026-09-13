"""Structured reports and presentation-only progress, independent of data writes."""

import json
import logging
import shutil
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.text import Text


@dataclass(frozen=True)
class RangeDetail:
    start: date | None
    end: date | None
    reason: str
    count: int = 1

    def text(self):
        scope = (
            "当前全集"
            if self.start is None
            else str(self.start)
            if self.start == self.end
            else f"{self.start}..{self.end}"
        )
        return f"{scope} | {self.reason} | {self.count} 段"


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
        self.stage = "准备"
        self.scope = ""
        self.slice_started = self.start
        self.samples = deque(maxlen=20)
        self.event("invocation_started", api=api.name, command=command)
        (self.folder / ".write-check").write_text("", encoding="utf-8")
        (self.folder / ".write-check").unlink()

    def event(self, event, level=logging.INFO, **fields):
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
            click.echo("日志输出失败：日志不完整；已确认提交的数据保留，本次以失败退出。", err=True)
        except OSError:
            pass

    def report(self, name, heading, lines, *, explicit=False, sections=None):
        """Summary is never truncated. Each detail section has its own display budget."""
        started = self.clock()
        path = self.folder / f"{name}.md"
        temporary = path.with_suffix(".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                stream.write(f"# {heading}\n\n")
                for line in lines:
                    stream.write(line + "\n\n")
                if sections is not None:
                    for title, items in sections:
                        stream.write(f"## {title}（{sum(i.count for i in items)} 段）\n\n")
                        for item in items:
                            stream.write(f"- {item.text()}\n")
                        if not items:
                            stream.write("无。\n")
                        stream.write("\n")
            temporary.replace(path)
            if not self.quiet or explicit:
                click.echo(heading)
                if sections is None:  # Legacy general-purpose report callers.
                    for line in lines[: self.settings.report_max_items]:
                        click.echo(line)
                    omitted = len(lines) - self.settings.report_max_items
                    if omitted > 0:
                        click.echo(f"另有 {omitted} 条，完整内容见文件。")
                else:
                    for line in lines:
                        click.echo(line)
                    for title, items in sections:
                        if not items:
                            continue
                        grouped = merge_ranges(items)
                        click.echo(f"\n{title}（{sum(i.count for i in items)} 段）")
                        for item in grouped[: self.settings.report_max_items]:
                            text = item.text()
                            if shutil.get_terminal_size((80, 24)).columns < 65:
                                text = text.replace(" | ", "\n  ")
                            click.echo("  " + text)
                        omitted = len(grouped) - self.settings.report_max_items
                        if omitted > 0:
                            click.echo(f"  另有 {omitted} 个范围，完整内容见文件。")
            click.echo(f"报告：{path}")
            return path
        finally:
            self.report_seconds += self.clock() - started

    def begin(self, total):
        self.total = total
        if not total or self.quiet or self.settings.progress == "off":
            return
        if not self.settings.plain and sys.stderr.isatty():
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
            self.task = self.progress.add_task("下载", total=total, detail="ETA 暂不可估计")
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
            self.stage = stage

    def begin_slice(self, scope):
        with self.lock:
            self.scope = scope
            self.slice_started = self.clock()
            self.stage = "准备请求"

    def attempt(self):
        with self.lock:
            self.attempts += 1

    def receive(self, count):
        with self.lock:
            self.received += count
            self.stage = "已取得/暂存"

    def snapshot(self):
        with self.lock:
            elapsed = max(self.clock() - self.start, 0.001)
            eta = None
            # Use recent complete logical slices, including all waits and failed attempts.
            if (
                len(self.samples) >= 5
                and sum(self.samples) >= 10
                and self.stage not in {"重试等待", "合并提交", "停止"}
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
        eta = f"约 {state['eta']:.0f}s" if state["eta"] is not None else "暂不可估计"
        text = (
            f"{state['stage']} {state['scope']}; 失败 {state['failed']} 空 {state['empty']}; "
            f"已取得/暂存 {state['received']} 行; 已确认入库输入 {state['rows']} 行; "
            f"HTTP {state['http_rate']:.2f}/s; 入库 {state['row_rate']:.1f} 行/s; ETA {eta}"
        )
        with self.lock:
            if self.progress:
                self.progress.update(self.task, completed=state["done"], detail=text)
                self.progress.refresh()
            elif final or self.clock() - self.last_progress >= self.settings.progress_interval:
                click.echo(
                    f"进度 {state['done']}/{state['total']}; 耗时 {state['elapsed']:.1f}s; {text}",
                    err=True,
                )
                self.last_progress = self.clock()

    def advance(self, done, total, rows, attempts, failed, empty=0, *, stopped=False):
        with self.lock:
            self.samples.append(max(0, self.clock() - self.slice_started))
            self.done, self.total, self.rows = done, total, rows
            self.attempts, self.failed, self.empty = attempts, failed, empty
            self.stage = "停止" if stopped else "分段处理结束"
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

    def close(self):
        self.stop_progress()
        try:
            self.handler.close()
        except OSError:
            self.output_failure()
