"""Compare renderer/logging cost with identical fake HTTP and real PostgreSQL work."""

import argparse
import io
import json
import os
import platform
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
from flow import rows, wire
from run import FakeResponse, measured, summarize

from tushare_downloader.apis import get_api
from tushare_downloader.client import TushareClient
from tushare_downloader.config import Settings
from tushare_downloader.download import execute
from tushare_downloader.storage import Store


class TerminalBuffer(io.StringIO):
    def isatty(self):
        return True


def run(args):
    if args.repeat < 5 or args.rows < 2 or args.days < 5:
        raise ValueError("Use at least 5 repeats, 2 rows per day and 5 days.")
    dsn = os.environ.get("BENCH_DATABASE_URL")
    if not dsn:
        raise ValueError("Set the dedicated BENCH_DATABASE_URL.")
    root = Path(args.output) / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-output-" + uuid4().hex[:8]
    )
    root.mkdir(parents=True)
    api = get_api("daily_basic")
    first = date(2024, 1, 1)
    last = first + timedelta(days=args.days - 1)
    bodies = {
        (first + timedelta(days=i)).strftime("%Y%m%d"): wire(
            api, rows(api, first + timedelta(days=i), args.rows)
        )
        for i in range(args.days)
    }
    variants = [
        ("rich", False, "auto", "INFO"),
        ("plain", True, "auto", "INFO"),
        ("rich_progress_off", False, "off", "INFO"),
        ("plain_progress_off", True, "off", "INFO"),
        ("rich_debug", False, "auto", "DEBUG"),
        ("plain_debug", True, "auto", "DEBUG"),
    ]
    samples = []

    class Session:
        def post(self, url, **kwargs):
            return FakeResponse(bodies[kwargs["json"]["params"]["trade_date"]])

    def client_factory(settings, **kwargs):
        return TushareClient(settings, session=Session(), **kwargs)

    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
        if conn.info.dbname != "tushare_bench" or conn.info.user != "tushare_bench":
            raise ValueError("Database AND user must be tushare_bench.")
        store = Store(conn)
        with store.writer():
            identity = store.initialize()
            # Rotate execution order to reduce systematic first/last-case bias.
            for iteration in range(args.repeat):
                ordered = (
                    variants[iteration % len(variants) :] + variants[: iteration % len(variants)]
                )
                for name, plain, progress, level in ordered:
                    store.clean(api, apply=True, database="tushare_bench", database_id=identity)
                    folder = root / name / str(iteration + 1)
                    settings = Settings(
                        token="benchmark-fixture",
                        calendar_filter="off",
                        requests_per_minute=10**9,
                        plain=plain,
                        progress=progress,
                        log_level=level,
                        log_dir=folder / "logs",
                        report_dir=folder / "reports",
                    )
                    capture = TerminalBuffer()

                    def operation():
                        with redirect_stdout(capture), redirect_stderr(capture):
                            code = execute(
                                store,
                                api,
                                "fetch",
                                settings,
                                start=first,
                                end=last,
                                client_factory=client_factory,
                            )
                        assert code == 0
                        return {"exit_code": code}

                    result = measured(operation)
                    events = [
                        json.loads(line)
                        for p in settings.log_dir.glob("*.jsonl")
                        for line in p.read_text().splitlines()
                    ]
                    final = next(e for e in events if e["event"] == "invocation_finished")
                    assert final["data_requests"] == args.days
                    assert final["committed_rows"] == args.rows * args.days
                    assert store.counts(api) == (args.rows * args.days, 0)
                    output = capture.getvalue()
                    assert ("\x1b[" in output) != plain, "Requested renderer was not exercised"
                    if plain:
                        assert "\r" not in output
                    sample = {
                        **final,
                        **result,
                        "scenario": name,
                        "iteration": iteration + 1,
                        "terminal_bytes": len(output.encode()),
                        "log_events": len(events),
                        "baseline_rows_per_day": args.rows,
                        "days": args.days,
                    }
                    samples.append(sample)
                    with (root / "samples.jsonl").open("a") as stream:
                        stream.write(json.dumps(sample) + "\n")
            store.clean(api, apply=True, database="tushare_bench", database_id=identity)
        environment = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "postgresql": conn.execute("SHOW server_version").fetchone()[0],
            "software_sha": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "terminal": "120x24 TTY-like StringIO; actual Rich renderer; excludes terminal emulator paint cost",
            "fixture": "50 date blocks by default; fixed successful HTTP responses, real dedicated PostgreSQL",
            "waits": "request limit 1e9/minute; no injected sleeps, errors or network",
            "memory": "tracemalloc Python allocation peak, not process RSS or PostgreSQL memory",
            "setup": "fixtures, table cleanup and post-run verification excluded from measured wall time",
            "order": "variant order rotated once per iteration",
        }
    (root / "environment.json").write_text(json.dumps(environment, indent=2))
    summary = summarize(samples)
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"output": str(root), "summary": summary}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--days", type=int, default=50)
    parser.add_argument("--output", default="benchmarks/results")
    args = parser.parse_args()
    for variable in ("NO_COLOR", "PLAIN"):
        os.environ.pop(variable, None)
    os.environ.update(TERM="xterm-256color", COLUMNS="120", LINES="24")
    run(args)
