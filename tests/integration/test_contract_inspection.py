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
