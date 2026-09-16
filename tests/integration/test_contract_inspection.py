import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.storage import StorageError


def test_numeric_typmod_is_not_same_contract(db):
    db.initialize()
    db.conn.execute("ALTER TABLE raw.daily ALTER COLUMN close TYPE numeric(10,2)")
    with pytest.raises(StorageError):
        db.validate(get_api("daily"))


def test_view_cannot_impersonate_managed_table(db):
    db.initialize()
    db.conn.execute("ALTER TABLE raw.daily RENAME TO displaced_daily")
    db.conn.execute("CREATE VIEW raw.daily AS SELECT * FROM raw.displaced_daily")
    with pytest.raises(StorageError):
        db.validate(get_api("daily"))


def test_inspect_empty_snapshot_and_daily(db):
    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import _read

    db.initialize()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
    )
    daily = _read(cfg, "daily", True)
    assert daily["ok"]
    assert daily["Latest data"] == "No active data"
    assert daily["Active / Stale rows"] == (0, 0)
    assert daily["Last successful fetch (UTC)"] == "Never"
    assert daily["Installed schema"] == "1.0.0"
    assert _read(cfg, "stock_basic", False)["Latest data"] == "N/A (snapshot)"


def test_read_does_not_take_writer_lock(db):
    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import inspect_dataset

    db.initialize()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
    )
    with db.writer():
        assert inspect_dataset(cfg, "daily")["ok"]


@pytest.mark.parametrize("empty", [False, True])
def test_inspect_preserves_success_when_later_attempts_fail(db, empty):
    from datetime import UTC, date, datetime, timedelta

    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import _read
    from tushare_downloader.planning import Block

    db.initialize()
    api = get_api("daily")
    day = date(2026, 8, 3)
    stamp = datetime(2026, 8, 4, tzinfo=UTC)
    first = Block(1, day, day, day, day)
    second = Block(
        2,
        day + timedelta(days=1),
        day + timedelta(days=1),
        day + timedelta(days=1),
        day + timedelta(days=1),
    )
    rows = [] if empty else [("000001.SZ", day, *[None for _ in api.fields[2:]])]
    db.merge(api, first, rows, stamp)
    later = stamp + timedelta(hours=1)
    db.failed(api, first, later)
    db.merge(api, second, [], later)
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
    )
    before = db.conn.execute("SELECT * FROM meta.slices ORDER BY block_id").fetchall()
    result = _read(cfg, "daily", True)
    assert result["ok"]
    assert result["Last successful fetch (UTC)"] == later
    assert result["Last recorded attempt (UTC)"] == later
    assert result["Latest attempt outcomes"] == [("failed", 1), ("success", 1)]
    assert result["Latest data"] == ("No active data" if empty else day)
    assert result["Active / Stale rows"] == (0 if empty else 1, 0)
    assert db.conn.execute("SELECT * FROM meta.slices ORDER BY block_id").fetchall() == before

    newest = later + timedelta(hours=1)
    db.failed(api, second, newest)
    result = _read(cfg, "daily", False)
    assert result["Last successful fetch (UTC)"] == later
    assert result["Last recorded attempt (UTC)"] == newest
    assert result["Latest attempt outcomes"] == [("failed", 1)]
    assert "Active / Stale rows" not in result
