"""Real PostgreSQL checks for new contracts and the additive registry upgrade."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tushare_downloader import storage
from tushare_downloader.apis import APIS, get_api
from tushare_downloader.planning import Block
from tushare_downloader.storage import StorageError

pytestmark = pytest.mark.integration
DAY = date(2026, 8, 3)
BLOCK = Block(1, DAY, DAY, DAY, DAY)
STAMP = datetime(2026, 8, 4, tzinfo=UTC)


def row(api, key="000001.SZ", value="1"):
    return (
        key,
        DAY,
        *[
            Decimal(value) if f.kind == "decimal" else None if f.name == "suspend_timing" else "S"
            for f in api.fields[2:]
        ],
    )


@pytest.mark.parametrize("name", ["daily", "adj_factor", "stk_limit", "suspend_d"])
def test_new_api_reconciliation_and_empty_preservation(db, name):
    db.initialize()
    api = get_api(name)
    assert db.merge(api, BLOCK, [row(api), row(api, "000002.SZ")], STAMP).inserted == 2
    assert db.merge(api, BLOCK, [row(api)], STAMP, reconcile=True).stale == 1
    assert db.counts(api) == (1, 1)
    db.merge(api, BLOCK, [], STAMP, reconcile=True)
    assert db.counts(api) == (1, 1)
    assert db.merge(api, BLOCK, [row(api, "000002.SZ")], STAMP).reactivated == 1
    assert db.counts(api) == (2, 0)


def test_additive_upgrade_preserves_identity_rows_and_observation(db, monkeypatch):
    old = {name: APIS[name] for name in ("daily_basic", "stock_basic")}
    monkeypatch.setattr(storage, "APIS", old)
    identity = db.initialize()
    api = get_api("daily_basic")
    db.merge(api, BLOCK, [row(api)], STAMP)
    observed = db.observation(api, BLOCK)
    monkeypatch.setattr(storage, "APIS", APIS)
    assert db.initialize() == identity
    assert db.initialize() == identity
    assert db.observation(api, BLOCK) == observed
    assert db.counts(api) == (1, 0)
    for registered in APIS.values():
        assert db.validate(registered) == identity


def test_additive_upgrade_rolls_back_when_later_table_is_unmanaged(db, monkeypatch):
    monkeypatch.setattr(
        storage, "APIS", {name: APIS[name] for name in ("daily_basic", "stock_basic")}
    )
    identity = db.initialize()
    before = db.identity()
    db.conn.execute("CREATE TABLE raw.suspend_d (unmanaged text)")
    monkeypatch.setattr(storage, "APIS", APIS)
    with pytest.raises(StorageError, match="ownership"):
        db.initialize()
    assert db.identity() == before
    assert db.identity()[0] == identity
    for name in ("daily", "adj_factor", "stk_limit"):
        assert db.conn.execute("SELECT to_regclass(%s)", (f"raw.{name}",)).fetchone()[0] is None


@pytest.mark.parametrize("name", ["daily", "adj_factor", "stk_limit", "suspend_d"])
@pytest.mark.parametrize("command", ["fetch", "refresh", "update"])
def test_daily_commands_use_expected_scope_and_preserve_policy(
    db, tmp_path, monkeypatch, name, command
):
    from datetime import timedelta

    from tushare_downloader.apis import ApiSpec
    from tushare_downloader.client import ApiResult
    from tushare_downloader.config import Settings
    from tushare_downloader.download import execute

    api = get_api(name)
    monkeypatch.setattr(ApiSpec, "available_end", lambda self, now: DAY)
    db.initialize()
    block = Block((DAY - api.block_origin).days, DAY, DAY, DAY, DAY)
    db.merge(api, block, [row(api), row(api, "000002.SZ")], STAMP)
    db.failed(api, block, STAMP)
    incoming = list(row(api, value="2"))
    if name == "suspend_d":
        incoming[-1] = "R"
    calls = []

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, actual, params):
            assert actual == api
            calls.append(params)
            return ApiResult((tuple(incoming), row(api, "000003.SZ")), 2, 0, 1)

    settings = Settings(
        token="fixture",
        plain=True,
        progress="off",
        lookback_days=1,
        max_age=timedelta(0),
        report_dir=tmp_path / "reports",
        log_dir=tmp_path / "logs",
    )
    dates = {} if command == "update" else {"start": DAY, "end": DAY}
    assert execute(db, api, command, settings, client_factory=Client, **dates) == 0
    assert calls == [{"trade_date": "20260803"}]
    assert db.counts(api) == ((2, 1) if command == "refresh" else (3, 0))
    assert db.observation(api, block).failed is False


def test_suspension_conflict_leaves_day_untouched_and_reports_failure(db, tmp_path):
    from tushare_downloader.client import ApiResult, parse_rows
    from tushare_downloader.config import Settings
    from tushare_downloader.download import execute

    api = get_api("suspend_d")
    db.initialize()
    block = Block((DAY - api.block_origin).days, DAY, DAY, DAY, DAY)
    db.merge(api, block, [row(api)], STAMP)
    db.failed(api, block, STAMP)

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, actual, params):
            fields = list(api.field_names)
            items = [["000001.SZ", "20260803", None, "S"], ["000001.SZ", "20260803", None, "R"]]
            values, received, duplicates = parse_rows({"fields": fields, "items": items}, api)
            return ApiResult(values, received, duplicates, 1)

    settings = Settings(
        token="fixture",
        plain=True,
        progress="off",
        report_dir=tmp_path / "reports",
        log_dir=tmp_path / "logs",
    )
    assert execute(db, api, "fetch", settings, start=DAY, end=DAY, client_factory=Client) == 1
    assert db.conn.execute("SELECT suspend_type, _is_stale FROM raw.suspend_d").fetchall() == [
        ("S", False)
    ]
    assert db.observation(api, block).failed
    report = next(settings.report_dir.glob("*/report.md")).read_text()
    assert "duplicate_conflict" in report
