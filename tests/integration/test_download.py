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
    report = next((tmp_path / "reports").glob("*/report.md")).read_text()
    assert "| L | Received | 1 |" in report
    assert "| D | Failed | 0 |" in report
    assert "| P | Not attempted | 0 |" in report
    assert "not independently committed" in report
    assert "| Full snapshot | Request:" in report


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
    assert "1 unknown" in text and "1 unattempted" in text
    assert "Commit outcome unknown; stopped without replay" in text
    assert "| Scope | Plan | Outcome | Attempts | Committed rows |" in text
    assert "| commit_unknown | 1 | unknown |" in text
    assert "Original plan" in text


def test_calendar_default_filters_weekend_without_success_records(db, tmp_path):
    db.initialize()
    first, last = date(2024, 1, 5), date(2024, 1, 8)
    assert (
        execute(
            db,
            API,
            "fetch",
            config(tmp_path),
            start=first,
            end=last,
            client_factory=factory([result(first), result(last)]),
        )
        == 0
    )
    assert db.counts(API) == (2, 0)
    assert db.conn.execute("SELECT count(*) FROM meta.slices").fetchone()[0] == 2
    report = next((tmp_path / "reports").glob("*/report.md")).read_text()
    request_section = report.split("### Request", 1)[1].split("\n##", 1)[0]
    assert "2024-01-05" in request_section and "2024-01-08" in request_section
    assert "2024-01-06" not in request_section and "2024-01-07" not in request_section
    # Explicit bypass still respects local successful records; only the weekend remains.
    saturday, sunday = date(2024, 1, 6), date(2024, 1, 7)
    assert (
        execute(
            db,
            API,
            "fetch",
            config(tmp_path),
            start=first,
            end=last,
            ignore_calendar=True,
            client_factory=factory([result(saturday), result(sunday)]),
        )
        == 0
    )
    assert db.counts(API) == (4, 0)


def test_calendar_dry_run_missing_cache_has_no_db_writes(db, tmp_path):
    db.initialize()
    settings = replace(
        config(tmp_path), calendar_filter="calendar", calendar_cache_dir=tmp_path / "calendar"
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Network during dry run")

    assert (
        execute(
            db,
            API,
            "fetch",
            settings,
            start=date(2024, 1, 2),
            end=date(2024, 1, 3),
            dry_run=True,
            client_factory=forbidden,
        )
        == 1
    )
    assert db.counts(API) == (0, 0)
    assert db.conn.execute("SELECT count(*) FROM meta.slices").fetchone()[0] == 0
    assert not settings.calendar_cache_dir.exists()
    report = next(settings.report_dir.glob("*/report.md")).read_text()
    assert "incomplete" in report and "Data requests | 0" in report


@pytest.mark.parametrize("fault", ["network", "business", "missing_dates", "cache_write"])
def test_calendar_preparation_failure_never_starts_data_requests(db, tmp_path, monkeypatch, fault):
    db.initialize()
    settings = replace(
        config(tmp_path), calendar_filter="calendar", calendar_cache_dir=tmp_path / "calendar"
    )
    calls = []

    class CalendarClient:
        attempts = 0
        closed = False

        def __init__(self, settings, on_attempt=None):
            self.on_attempt = on_attempt

        def query(self, api, params):
            calls.append(api.name)
            self.attempts += 1
            self.on_attempt(api.name, self.attempts)
            assert api.name == "trade_cal"
            if fault in {"network", "business"}:
                raise RequestError(fault, "calendar unavailable")
            values = () if fault == "missing_dates" else (("SSE", date(2024, 1, 2), Decimal(1)),)
            return ApiResult(values, len(values), 0, 1)

        def close(self):
            self.closed = True

    if fault == "cache_write":

        def deny(*args, **kwargs):
            raise OSError("simulated cache failure")

        monkeypatch.setattr("tushare_downloader.calendar._write", deny)

    code = execute(
        db,
        API,
        "fetch",
        settings,
        start=date(2024, 1, 2),
        end=date(2024, 1, 2),
        client_factory=CalendarClient,
    )
    assert code == 1 and calls == ["trade_cal"]
    assert db.counts(API) == (0, 0)
    assert db.conn.execute("SELECT count(*) FROM meta.slices").fetchone()[0] == 0
    report = next(settings.report_dir.glob("*/report.md")).read_text()
    assert "Data requests | 0" in report
    assert "incomplete" in report and "--ignore-calendar" in report
    assert "Action" in report


@pytest.mark.parametrize(
    "threshold,failures,expected",
    [
        (2, (True, True, False, False), (0, 2, 2)),
        (0, (True, True, False, False), (2, 2, 0)),
        (2, (True, False, True, False), (2, 2, 0)),
        (1, (False, True, False, False), (1, 1, 2)),
    ],
)
def test_consecutive_failure_threshold_and_reset(db, tmp_path, threshold, failures, expected):
    db.initialize()
    settings = replace(config(tmp_path), max_consecutive_failed_slices=threshold)
    outcomes = [
        RequestError("network", "fixture") if failed else result(date(2024, 1, i + 2))
        for i, failed in enumerate(failures)
    ]
    assert (
        execute(
            db,
            API,
            "fetch",
            settings,
            start=date(2024, 1, 2),
            end=date(2024, 1, 5),
            client_factory=factory(outcomes),
        )
        == 1
    )
    events = [
        json.loads(line)
        for p in settings.log_dir.glob("*.jsonl")
        for line in p.read_text().splitlines()
    ]
    final = next(e for e in events if e["event"] == "invocation_finished")
    assert (final["success"], final["failed"], final["unattempted"]) == expected
    assert final["success"] + final["failed"] + final["unattempted"] == 4
    assert db.counts(API) == (expected[0], 0)
