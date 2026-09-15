"""Full executor benchmark: fake HTTP + real PostgreSQL + normal logs/reports."""

import argparse
import io
import json
import os
import platform
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
from run import FakeResponse, measured, summarize

from tushare_downloader.apis import APIS, get_api
from tushare_downloader.client import TushareClient
from tushare_downloader.config import Settings
from tushare_downloader.download import execute
from tushare_downloader.planning import Block
from tushare_downloader.storage import Store


def rows(api, day, count, value="1"):
    if api.query_kind == "time-range":
        return tuple(
            (
                f"{i:06}.SZ",
                day,
                *(
                    Decimal(value)
                    if f.kind == "decimal"
                    else None
                    if f.name == "suspend_timing"
                    else "S"
                    for f in api.fields[2:]
                ),
            )
            for i in range(count)
        )
    values = []
    for i in range(count):
        row = [None] * len(api.fields)
        row[0] = f"{i:06}.SZ"
        row[api.field_names.index("name")] = value
        row[api.field_names.index("list_status")] = "L"
        values.append(tuple(row))
    return tuple(values)


def wire(api, values):
    def encode(value):
        if isinstance(value, Decimal):
            return str(value)
        if hasattr(value, "strftime"):
            return value.strftime("%Y%m%d")
        return value

    return json.dumps(
        {
            "code": 0,
            "data": {
                "fields": api.field_names,
                "items": [[encode(v) for v in row] for row in values],
            },
        }
    ).encode()


def run(args):
    if args.repeat < 5 or args.rows < 2:
        raise ValueError("repeat must be at least 5 and rows at least 2.")
    dsn = os.environ.get("BENCH_DATABASE_URL")
    if not dsn:
        raise ValueError("Set BENCH_DATABASE_URL to a dedicated benchmark database.")
    root = Path(args.output) / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-flow-" + uuid4().hex[:8]
    )
    root.mkdir(parents=True)
    samples = []
    cases = (
        "initial",
        "skip_all",
        "middle_failed",
        "partial_expired",
        "refresh_all",
        "append_update",
        "mutable_delete",
        "mutable_reappear",
        "empty",
        "duplicates",
        "partial_failure",
        "long_report",
    )
    with psycopg.connect(dsn, autocommit=True, connect_timeout=5) as conn:
        if conn.info.dbname != "tushare_bench" or conn.info.user != "tushare_bench":
            raise ValueError("Both database and user must be tushare_bench.")
        store = Store(conn)
        with store.writer():
            identity = store.initialize()
            for case in cases:
                for iteration in range(1, args.repeat + 1):
                    for candidate in (args.api, "stock_basic"):
                        store.clean(
                            get_api(candidate),
                            apply=True,
                            database="tushare_bench",
                            database_id=identity,
                        )
                    api = get_api("stock_basic" if case.startswith("mutable") else args.api)
                    stamp = datetime.now(UTC)
                    end = get_api(args.api).available_end(stamp)
                    days = 100 if case == "long_report" else 5
                    start = end - timedelta(days=days - 1)
                    dates = (
                        [start + timedelta(days=i) for i in range(days)]
                        if api.query_kind == "time-range"
                        else [api.block_origin]
                    )
                    blocks = [
                        Block(
                            (day - api.block_origin).days if api.query_kind == "time-range" else 0,
                            day,
                            day,
                            day,
                            day,
                        )
                        for day in dates
                    ]
                    baseline = {b.id: rows(api, b.requested_start, args.rows) for b in blocks}
                    if case not in {"initial", "duplicates", "partial_failure", "long_report"}:
                        for i, block in enumerate(blocks):
                            if case == "append_update" and i >= 2:
                                continue
                            store.merge(api, block, baseline[block.id], stamp, reconcile=True)
                    if case == "middle_failed":
                        store.failed(api, blocks[2], stamp)
                    if case == "partial_expired":
                        conn.execute(
                            "UPDATE meta.slices SET last_reconciled_at=%s WHERE block_id %% 2=0",
                            (stamp - timedelta(days=2),),
                        )
                    if case == "mutable_reappear":
                        store.merge(
                            api,
                            blocks[0],
                            baseline[blocks[0].id][: args.rows // 2],
                            stamp,
                            reconcile=True,
                        )
                    bodies = {}
                    for i, block in enumerate(blocks):
                        values = baseline[block.id]
                        if case == "mutable_delete":
                            values = values[: args.rows // 2]
                        if case == "empty" or (case == "long_report" and i % 2):
                            values = ()
                        if case == "duplicates":
                            values = values + values[: max(1, args.rows // 10)]
                        key = (
                            block.requested_start.strftime("%Y%m%d")
                            if api.query_kind == "time-range"
                            else "L"
                        )
                        bodies[key] = wire(api, values)
                    if api.query_kind == "snapshot":
                        for status in ("D", "P", "G", "UN"):
                            bodies[status] = wire(api, ())
                    bad_key = dates[len(dates) // 2].strftime("%Y%m%d")

                    class Session:
                        def post(self, url, **kwargs):
                            params = kwargs["json"]["params"]
                            key = params.get("trade_date", params.get("list_status"))
                            response = FakeResponse(bodies[key])
                            if case == "partial_failure" and key == bad_key:
                                response.status_code = 503
                            return response

                    def client_factory(settings, **kwargs):
                        return TushareClient(
                            settings,
                            session=Session(),
                            sleep=lambda seconds: None,
                            jitter=lambda: 0,
                            **kwargs,
                        )

                    folder = root / case / str(iteration)
                    settings = Settings(
                        token="benchmark-fixture",
                        requests_per_minute=10**9,
                        lookback_days=2,
                        calendar_filter="off",
                        progress="off",
                        plain=True,
                        log_dir=folder / "logs",
                        report_dir=folder / "reports",
                    )
                    command = "fetch"
                    if case in {"partial_expired", "refresh_all", "empty"}:
                        command = "refresh"
                    if case == "refresh_all":
                        settings = replace(settings, max_age=timedelta(0))
                    if case == "empty":
                        settings = replace(settings, max_age=timedelta(0))
                    if case == "append_update" or case.startswith("mutable"):
                        command = "update"
                    dates_args = (
                        {"start": start, "end": end}
                        if command != "update" and api.query_kind == "time-range"
                        else {}
                    )
                    captured = io.StringIO()

                    def operation():
                        with redirect_stdout(captured), redirect_stderr(captured):
                            code = execute(
                                store,
                                api,
                                command,
                                settings,
                                client_factory=client_factory,
                                **dates_args,
                            )
                        if code != (1 if case == "partial_failure" else 0):
                            raise RuntimeError(f"{case} unexpected exit: {code}")
                        return {"exit_code": code}

                    sample = measured(operation)
                    events = [
                        json.loads(line)
                        for p in settings.log_dir.glob("*.jsonl")
                        for line in p.read_text().splitlines()
                    ]
                    finished = next(e for e in events if e["event"] == "invocation_finished")
                    sample = {
                        **finished,
                        **sample,
                        "scenario": case,
                        "iteration": iteration,
                        "baseline_rows_per_day": args.rows,
                        "start": str(start),
                        "end": str(end),
                    }
                    samples.append(sample)
                    with (root / "samples.jsonl").open("a") as stream:
                        stream.write(json.dumps(sample) + "\n")
            for candidate in (args.api, "stock_basic"):
                store.clean(
                    get_api(candidate), apply=True, database="tushare_bench", database_id=identity
                )
        environment = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "postgresql": conn.execute("SHOW server_version").fetchone()[0],
            "mode": "full executor: fake HTTP + real PostgreSQL",
            "daily_api": args.api,
            "network_and_waits": "disabled in fixture client; production logic unchanged",
            "progress": "off; normal reports and INFO logs enabled",
            "calendar": "off explicitly: fixed date fixture; calendar comparisons run separately",
            "peak_memory": "tracemalloc Python allocations; server/RSS excluded",
            "setup": "database/HTTP fixture preparation and summary reading excluded from wall time",
        }
        (root / "environment.json").write_text(json.dumps(environment, indent=2))
    summary = summarize(samples)
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# End-to-end flow benchmark",
        "",
        "Synthetic HTTP, real PostgreSQL and default logging/reporting; at least five samples per scenario.",
        "",
        "| Scenario | Samples | Median seconds | Minimum | Maximum | MAD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in summary:
        lines.append(
            f"| {item['scenario']} | {item['runs']} | {item['median_seconds']:.6f} | {item['min_seconds']:.6f} | {item['max_seconds']:.6f} | {item['mad_seconds']:.6f} |"
        )
    (root / "summary.md").write_text("\n".join(lines) + "\n")
    print(root / "summary.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        choices=[a.name for a in APIS.values() if a.query_kind == "time-range"],
        default="daily_basic",
    )
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--output", default="benchmarks/results")
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, RuntimeError, psycopg.Error) as error:
        raise SystemExit(
            str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
        ) from None
