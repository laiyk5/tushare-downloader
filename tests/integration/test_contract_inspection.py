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
