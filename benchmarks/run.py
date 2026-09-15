"""Reproducible benchmarks. Run with uv run python benchmarks/run.py --help."""

import argparse
import io
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg

from tushare_downloader.apis import get_api
from tushare_downloader.client import RequestError, TushareClient
from tushare_downloader.config import Settings, load_settings
from tushare_downloader.planning import Block, Observation, block_id, blocks, request_reason
from tushare_downloader.reporting import RangeDetail, Reporter
from tushare_downloader.storage import Store

DAY = date(2024, 1, 2)
STAMP = datetime(2024, 1, 3, tzinfo=UTC)
API = get_api("daily_basic")
BLOCK = Block(block_id(DAY, API.block_origin, 1), DAY, DAY, DAY, DAY)


def payload(rows, duplicate=False):
    items = [[f"{i:06}.SZ", "20240102", *[1.25 for _ in API.fields[2:]]] for i in range(rows)]
    if duplicate:
        items += items[: max(1, rows // 10)]
    return json.dumps({"code": 0, "data": {"fields": API.field_names, "items": items}}).encode()


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, body):
        self.body = body

    def iter_content(self, chunk_size):
        for i in range(0, len(self.body), chunk_size):
            yield self.body[i : i + chunk_size]

    def close(self):
        pass


class FakeSession:
    def __init__(self, body):
        self.body = body

    def post(self, *args, **kwargs):
        return FakeResponse(self.body)


class TTY(io.StringIO):
    def isatty(self):
        return True


def measured(operation):
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = operation()
        elapsed = time.perf_counter() - started
        peak = tracemalloc.get_traced_memory()[1]
        return {**result, "wall_seconds": elapsed, "python_peak_bytes": peak}
    finally:
        tracemalloc.stop()


def transport_operation(body):
    def operation():
        # Fake HTTP: no network or rate-limit waits; same parser and byte budget.
        with TushareClient(
            Settings(token="benchmark-fixture", requests_per_minute=10**9),
            session=FakeSession(body),
        ) as client:
            result = client.query(API, {})
            return {
                "input_rows": result.received_rows,
                "unique_rows": len(result.rows),
                "duplicate_rows": result.duplicate_rows,
                "http_attempts": client.attempts,
                "response_bytes": client.response_bytes,
                **client.timings,
            }

    return operation


def decision_operation(kind, count):
    def operation():
        now = STAMP + timedelta(days=30)
        selected = blocks(
            DAY,
            DAY + timedelta(days=count - 1),
            origin=API.block_origin,
            size=1,
            available_start=DAY,
            available_end=DAY + timedelta(days=count - 1),
        )
        needed = 0
        command = "fetch"
        for i, block in enumerate(selected):
            obs = Observation("1", block.requested_start, block.requested_end, now, now)
            if kind == "initial":
                obs = None
            elif kind == "middle_failed":
                obs = replace(obs, failed=i == len(selected) // 2)
            elif kind == "partial_expired":
                command = "refresh"
                obs = replace(obs, last_reconciled_at=now - timedelta(days=2) if i % 2 else now)
            elif kind == "refresh_all":
                command = "refresh"
                obs = replace(obs, last_reconciled_at=now - timedelta(days=2))
            elif kind == "update_window":
                command = "update"
            elif kind == "empty":
                obs = replace(obs, empty=True)
            needed += (
                request_reason(
                    command,
                    block,
                    obs,
                    spec_version="1",
                    now=now,
                    max_age=timedelta(days=1),
                    empty_recheck_age=timedelta(days=1),
                )
                is not None
            )
        return {
            "candidate_blocks": len(selected),
            "planned_requests": needed,
            "skipped": len(selected) - needed,
        }

    return operation


def block_operation(size):
    def operation():
        demand = [DAY + timedelta(days=i) for i in range(0, 365, 2)]
        ids = {block_id(day, DAY, size) for day in demand}
        return {
            "block_days": size,
            "demand_days": len(demand),
            "planned_requests": len(ids),
            "requested_days": len(ids) * size,
            "extra_days": len(ids) * size - len(demand),
        }

    return operation


def report_operation(root, rows, variant):
    def operation():
        settings = Settings(
            log_dir=root / "logs",
            report_dir=root / "reports",
            plain=variant != "rich",
            progress="off" if variant == "off" else "auto",
            log_level="DEBUG" if variant == "debug" else "INFO",
        )
        stream = TTY() if variant == "rich" else io.StringIO()
        with redirect_stdout(stream), redirect_stderr(stream):
            reporter = Reporter(settings, API, "benchmark")
            try:
                items = [
                    RangeDetail(DAY + timedelta(days=i * 2), DAY + timedelta(days=i * 2), "fixture")
                    for i in range(rows)
                ]
                reporter.report(
                    "before",
                    "Presentation overhead",
                    ["Fixed test input"],
                    sections=[("Scope", items)],
                )
                reporter.begin(5)
                for i in range(5):
                    reporter.begin_slice("fixture")
                    reporter.phase("HTTP request")
                    reporter.receive(rows)
                    reporter.event("phase", level=10, stage="fixture")
                    reporter.advance(i + 1, 5, (i + 1) * rows, i + 1, 0)
                reporter.stop_progress()
                return {
                    "detail_rows": rows,
                    "variant": variant,
                    "report_seconds": reporter.report_seconds,
                    "log_seconds": reporter.handler.seconds,
                    "rendered_chars": len(stream.getvalue()),
                }
            finally:
                reporter.close()

    return operation


def summarize(samples):
    groups = {}
    for sample in samples:
        groups.setdefault(sample["scenario"], []).append(sample["wall_seconds"])
    return [
        {
            "scenario": name,
            "runs": len(values),
            "median_seconds": statistics.median(values),
            "min_seconds": min(values),
            "max_seconds": max(values),
            "mad_seconds": statistics.median(abs(v - statistics.median(values)) for v in values),
        }
        for name, values in groups.items()
    ]


def run(args):
    if args.repeat < 5 or args.rows < 1:
        raise ValueError("--repeat must be at least 5 and --rows must be positive.")
    root = Path(args.output) / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    )
    root.mkdir(parents=True)
    samples = []
    metadata = {
        "mode": args.mode,
        "repeat": args.repeat,
        "rows": args.rows,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "peak_metric": "tracemalloc Python allocations; excludes PostgreSQL server/RSS",
        "memory_instrumentation": "enabled for all trials; adds overhead",
        "fake_http_waits": "disabled only in cpu mode",
    }
    from importlib.metadata import version

    metadata["dependencies"] = {
        name: version(name) for name in ("tushare-downloader", "psycopg", "requests", "rich")
    }

    def trial(name, operation, iteration):
        sample = {"scenario": name, "iteration": iteration, **measured(operation)}
        samples.append(sample)
        with (root / "samples.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(sample, ensure_ascii=False) + "\n")

    if args.mode == "cpu":
        cases = [
            ("http_parse", transport_operation(payload(args.rows))),
            ("http_parse_duplicates", transport_operation(payload(args.rows, True))),
        ]
        cases += [
            (f"plan_{kind}", decision_operation(kind, args.rows))
            for kind in (
                "initial",
                "skip_all",
                "middle_failed",
                "partial_expired",
                "refresh_all",
                "update_window",
                "empty",
            )
        ]
        cases += [(f"block_{size}d", block_operation(size)) for size in (1, 7, 30)]
        cases += [
            (f"report_{variant}", report_operation(root, args.rows, variant))
            for variant in ("plain", "off", "debug", "rich")
        ]
        for name, operation in cases:
            for i in range(args.repeat):
                trial(name, operation, i + 1)
    elif args.mode == "database":
        dsn = os.environ.get("BENCH_DATABASE_URL")
        if not dsn:
            raise ValueError(
                "Database benchmarks require BENCH_DATABASE_URL; production configuration is not used."
            )
        with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
            if conn.info.dbname != "tushare_bench" or conn.info.user != "tushare_bench":
                raise ValueError("数据Both database and user must be tushare_bench.")
            metadata["postgresql_version"] = conn.execute("SHOW server_version").fetchone()[0]
            store = Store(conn)
            with store.writer():
                identity = store.initialize()
                # Prepare typed data outside measured database sections.
                with TushareClient(
                    Settings(token="fixture", requests_per_minute=10**9),
                    session=FakeSession(payload(args.rows)),
                ) as client:
                    baseline = client.query(API, {}).rows
                for name in ("insert", "unchanged", "changed", "stale", "reactivate", "empty"):
                    for i in range(args.repeat):
                        store.clean(API, apply=True, database="tushare_bench", database_id=identity)
                        if name != "insert":
                            store.merge(API, BLOCK, baseline, STAMP)
                        incoming = baseline
                        if name == "changed":
                            incoming = tuple(
                                (*row[:2], *[None for _ in row[2:]]) for row in baseline
                            )
                        elif name == "stale":
                            incoming = baseline[: max(1, len(baseline) // 2)]
                        elif name == "reactivate":
                            store.merge(
                                API,
                                BLOCK,
                                baseline[: max(1, len(baseline) // 2)],
                                STAMP,
                                reconcile=True,
                            )
                        elif name == "empty":
                            incoming = ()

                        def operation():
                            counts = store.merge(
                                API,
                                BLOCK,
                                incoming,
                                STAMP + timedelta(days=1),
                                reconcile=name in {"stale", "empty"},
                            )
                            return {"input_rows": len(incoming), **asdict(counts)}

                        trial(f"db_{name}", operation, i + 1)
                store.clean(API, apply=True, database="tushare_bench", database_id=identity)
    else:
        settings = load_settings()
        settings.require_token()
        with TushareClient(settings) as client:
            for i in range(args.repeat):

                def operation():
                    previous = dict(client.timings)
                    attempts, size = client.attempts, client.response_bytes
                    result = client.query(API, {"trade_date": args.date.strftime("%Y%m%d")})
                    return {
                        "input_rows": result.received_rows,
                        "http_attempts": client.attempts - attempts,
                        "response_bytes": client.response_bytes - size,
                        **{key: value - previous[key] for key, value in client.timings.items()},
                    }

                trial("real_api_daily_basic", operation, i + 1)
        metadata["api_date"] = str(args.date)
        metadata["database_writes"] = False
    summary = summarize(samples)
    (root / "environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (root / "summary.md").open("w", encoding="utf-8") as stream:
        stream.write(
            "# Benchmark\n\nAll samples are retained; durations are seconds. Python memory sampling is enabled and adds overhead.\n\n"
        )
        stream.write(
            "| Scenario | Samples | Median | Minimum | Maximum | MAD |\n|---|---:|---:|---:|---:|---:|\n"
        )
        for item in summary:
            stream.write(
                f"| {item['scenario']} | {item['runs']} | {item['median_seconds']:.6f} | {item['min_seconds']:.6f} | {item['max_seconds']:.6f} | {item['mad_seconds']:.6f} |\n"
            )
    print(f"Benchmark completed: {root / 'summary.md'}")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("cpu", "database", "api"), default="cpu")
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--output", default="benchmarks/results")
    parser.add_argument("--date", type=date.fromisoformat, default=DAY)
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, psycopg.Error, OSError, RequestError) as error:
        # Never print a connection string or credentials from an exception.
        print(
            f"Benchmark failed: {error if isinstance(error, ValueError) else type(error).__name__}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
