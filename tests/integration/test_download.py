import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.client import ApiResult, RequestError
from tushare_downloader.config import Settings
from tushare_downloader.download import execute
from tushare_downloader.storage import Store

pytestmark = pytest.mark.integration
API = get_api("daily_basic")


def factory(outcomes):
    class Client:
        def __init__(self, *args, **kwargs):
            self.outcomes = iter(outcomes)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def query(self, *args):
            outcome = next(self.outcomes)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    return Client


def result(day, value="1"):
    return ApiResult((("001.SZ", day, *[Decimal(value) for _ in API.fields[2:]]),), 1, 0, 1)


def config(tmp_path):
    return Settings(
        token="test-secret",
        log_dir=tmp_path / "logs",
        report_dir=tmp_path / "reports",
        progress="off",
        plain=True,
    )


def test_failure_keeps_committed_days_and_rerun_only_retries_gap(db, tmp_path):
    db.initialize()
    days = [date(2024, 1, n) for n in (2, 3, 4)]
    settings = config(tmp_path)
    with db.writer():
        code = execute(
            db,
            API,
            "fetch",
            settings,
            start=days[0],
            end=days[2],
            client_factory=factory(
                [result(days[0]), RequestError("network", "offline"), result(days[2])]
            ),
        )
    assert code == 1 and db.counts(API) == (2, 0)
    with db.writer():
        code = execute(
            db,
            API,
            "fetch",
            settings,
            start=days[0],
            end=days[2],
            client_factory=factory([result(days[1])]),
        )
    assert code == 0 and db.counts(API) == (3, 0)
    events = [
        json.loads(line)
        for path in settings.log_dir.glob("*.jsonl")
        for line in path.read_text().splitlines()
    ]
    summaries = [e for e in events if e["event"] == "invocation_finished"]
    assert sorted(e["skipped"] for e in summaries) == [0, 2]
    assert "test-secret" not in "".join(path.read_text() for path in settings.log_dir.glob("*"))


def test_dry_run_needs_no_token_and_writes_no_database(db, tmp_path):
    db.initialize()
    settings = replace(config(tmp_path), token="")
    execute(db, API, "fetch", settings, start=date(2024, 1, 2), end=date(2024, 1, 3), dry_run=True)
    assert db.counts(API) == (0, 0)
    assert db.conn.execute("SELECT count(*) FROM meta.slices").fetchone()[0] == 0


def test_snapshot_partial_failure_is_not_merged(db, tmp_path):
    db.initialize()
    api = replace(get_api("stock_basic"), stale_scope_verified=True)
    values = ["001.SZ", *[None for _ in api.fields[1:]]]
    values[api.field_names.index("list_status")] = "L"
    first = ApiResult((tuple(values),), 1, 0, 1)
    code = execute(
        db,
        api,
        "update",
        config(tmp_path),
        client_factory=factory([first, RequestError("network", "offline")]),
    )
    assert code == 1 and db.counts(api) == (0, 0)


def test_business_error_stops_remaining_days(db, tmp_path):
    db.initialize()
    code = execute(
        db,
        API,
        "fetch",
        config(tmp_path),
        start=date(2024, 1, 2),
        end=date(2024, 1, 4),
        client_factory=factory([RequestError("business", "denied")]),
    )
    assert code == 1
    event = next(
        json.loads(line)
        for path in (tmp_path / "logs").glob("*")
        for line in path.read_text().splitlines()
        if json.loads(line)["event"] == "invocation_finished"
    )
    assert (event["failed"], event["unattempted"]) == (1, 2)


def test_commit_unknown_stops_and_is_not_counted_success(db, tmp_path, monkeypatch):
    from tushare_downloader.storage import CommitUnknown

    db.initialize()

    def unknown(*args, **kwargs):
        raise CommitUnknown("test")

    monkeypatch.setattr(Store, "merge", unknown)
    code = execute(
        db,
        API,
        "fetch",
        config(tmp_path),
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
        client_factory=factory([result(date(2024, 1, 2))]),
    )
    assert code == 1 and db.counts(API) == (0, 0)
    text = "".join(path.read_text() for path in (tmp_path / "reports").glob("*/report.md"))
    assert "Commit outcome unknown 1" in text and "未尝试 1" in text
