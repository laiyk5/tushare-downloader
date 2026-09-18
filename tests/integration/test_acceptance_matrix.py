"""Command × change kind × query shape acceptance; unsupported full scopes fail explicitly."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tushare_downloader.apis import ApiSpec, get_api
from tushare_downloader.client import ApiResult
from tushare_downloader.config import Settings
from tushare_downloader.download import execute
from tushare_downloader.planning import Block

pytestmark = pytest.mark.integration
DAY = date(2024, 1, 2)
STAMP = datetime(2024, 1, 3, tzinfo=UTC)


def make_row(api, key, value):
    values = [None] * len(api.fields)
    values[0] = key
    if api.query_kind == "time-range":
        values[1] = DAY
        values[2] = Decimal(value)
    else:
        values[api.field_names.index("name")] = value
        values[api.field_names.index("list_status")] = "L"
    return tuple(values)


@pytest.mark.parametrize("command", ["fetch", "refresh", "update"])
@pytest.mark.parametrize("change", ["append-only", "mutable"])
@pytest.mark.parametrize("shape", ["time-range", "snapshot"])
def test_command_matrix(db, tmp_path, monkeypatch, command, change, shape):
    db.initialize()
    monkeypatch.setattr(ApiSpec, "available_end", lambda self, now: DAY)
    api = replace(
        get_api("daily_basic" if shape == "time-range" else "stock_basic"), change_kind=change
    )
    block = Block((DAY - api.block_origin).days if shape == "time-range" else 0, DAY, DAY, DAY, DAY)
    if shape == "snapshot":
        block = Block(0, date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1))
    db.merge(api, block, [make_row(api, "old", "1"), make_row(api, "kept", "1")], STAMP)
    db.failed(api, block, STAMP)
    incoming = (make_row(api, "kept", "2"), make_row(api, "new", "3"))

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, api, params):
            rows = incoming if shape == "time-range" or params["list_status"] == "L" else ()
            return ApiResult(rows, len(rows), 0, 1)

    settings = Settings(
        token="fixture",
        lookback_days=1,
        max_age=__import__("datetime").timedelta(0),
        log_dir=tmp_path / "logs",
        report_dir=tmp_path / "reports",
        progress="off",
    )
    dates = {"start": DAY, "end": DAY} if command != "update" and shape == "time-range" else {}
    if change == "mutable" and shape == "time-range" and command == "update":
        with pytest.raises(ValueError, match="full-source boundary"):
            execute(db, api, command, settings, client_factory=Client, **dates)
        assert db.counts(api) == (2, 0)
        return
    assert execute(db, api, command, settings, client_factory=Client, **dates) == 0
    reconciles = command == "refresh" or (command == "update" and change == "mutable")
    assert db.counts(api) == ((2, 1) if reconciles else (3, 0))
    summary = [
        json.loads(line)
        for p in settings.log_dir.rglob("*.jsonl")
        for line in p.read_text().splitlines()
        if json.loads(line)["event"] == "invocation_finished"
    ][0]
    assert (summary["inserted"], summary["changed"], summary["unchanged"]) == (1, 1, 0)
    assert summary["committed_rows"] == sum(
        summary[k] for k in ("inserted", "changed", "unchanged", "reactivated")
    )
    assert (
        summary["success"]
        + summary["empty"]
        + summary["failed"]
        + summary["unknown"]
        + summary["unattempted"]
        == 1
    )


def test_mixed_row_results_agree_in_database_log_and_report(db, tmp_path):
    from datetime import timedelta

    from test_download import config, factory
    from test_storage import row

    api = get_api("daily_basic")
    db.initialize()
    block = Block((DAY - api.block_origin).days, DAY, DAY, DAY, DAY)
    db.merge(api, block, [row(key) for key in ["same", "changed", "returning", "missing"]], STAMP)
    db.conn.execute("UPDATE raw.daily_basic SET _is_stale=true WHERE ts_code='returning'")
    settings = replace(config(tmp_path), max_age=timedelta(0))
    incoming = (row("same"), row("changed", "2"), row("returning"), row("new"))
    assert (
        execute(
            db,
            api,
            "refresh",
            settings,
            start=DAY,
            end=DAY,
            client_factory=factory([ApiResult(incoming, 4, 0, 1)]),
        )
        == 0
    )
    observed = db.conn.execute(
        "SELECT ts_code, close, _is_stale FROM raw.daily_basic ORDER BY ts_code"
    ).fetchall()
    assert observed == [
        ("changed", Decimal(2), False),
        ("missing", Decimal(1), True),
        ("new", Decimal(1), False),
        ("returning", Decimal(1), False),
        ("same", Decimal(1), False),
    ]
    final = next(
        json.loads(line)
        for path in settings.log_dir.rglob("*.jsonl")
        for line in path.read_text().splitlines()
        if json.loads(line)["event"] == "invocation_finished"
    )
    assert [final[key] for key in ["inserted", "changed", "unchanged", "reactivated", "stale"]] == [
        1
    ] * 5
    assert final["committed_rows"] == 4
    report = next(settings.report_dir.glob("*/report.md")).read_text()
    for label in ["Inserted", "Updated", "Unchanged", "Reactivated"]:
        assert f"| {label} | 1 (25.0%) |" in report
    assert "| Newly stale | 1 / prior active 3 (33.3%) |" in report
    assert "| Committed input rows | 4 |" in report


def test_mixed_plan_counts_and_success_rate_exclude_skips_and_filters(db, tmp_path):
    from test_download import config, factory, result

    from tushare_downloader.client import RequestError

    api = get_api("daily_basic")
    db.initialize()
    first = date(2024, 1, 4)
    block = Block((first - api.block_origin).days, first, first, first, first)
    db.merge(api, block, result(first).rows, datetime(2024, 1, 5, tzinfo=UTC))
    settings = config(tmp_path)
    assert (
        execute(
            db,
            api,
            "fetch",
            settings,
            start=first,
            end=date(2024, 1, 9),
            client_factory=factory(
                [
                    result(date(2024, 1, 5)),
                    ApiResult((), 0, 0, 1),
                    RequestError("network", "fixture failure"),
                ]
            ),
        )
        == 1
    )
    events = [
        json.loads(line)
        for path in settings.log_dir.rglob("*.jsonl")
        for line in path.read_text().splitlines()
    ]
    final = next(event for event in events if event["event"] == "invocation_finished")
    assert [
        final[key]
        for key in ["success", "empty", "failed", "unknown", "unattempted", "skipped", "filtered"]
    ] == [1, 1, 1, 0, 0, 1, 2]
    assert sum(final[key] for key in ["success", "empty", "failed", "unknown", "unattempted"]) == 3
    assert 3 + final["skipped"] + final["filtered"] == 6
    report = next(settings.report_dir.glob("*/report.md")).read_text()
    assert "66.7%; failure rate: 33.3%" in report
    assert (
        "3 planned; 1 non-empty; 1 empty; 1 failed; 0 unknown; 0 unattempted; 1 skipped" in report
    )
    assert db.counts(api) == (2, 0)
