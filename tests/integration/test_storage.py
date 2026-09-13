from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import psycopg
import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.planning import Block
from tushare_downloader.storage import BusyError, StorageError, Store

pytestmark = pytest.mark.integration
API = replace(get_api("daily_basic"), stale_scope_verified=True)
DAY = date(2024, 1, 2)
BLOCK = Block(1, DAY, DAY, DAY, DAY)
STAMP = datetime(2024, 1, 3, tzinfo=UTC)


def row(key="001.SZ", value="1", day=DAY):
    return (key, day, *[Decimal(value) if value is not None else None for _ in API.fields[2:]])


def test_initialization_is_repeatable_and_rejects_damage(db):
    identity = db.initialize()
    assert db.initialize() == identity
    db.conn.execute("ALTER TABLE raw.daily_basic DROP COLUMN pe")
    with pytest.raises(StorageError):
        db.initialize()


def test_external_schema_not_adopted(db):
    db.conn.execute("CREATE SCHEMA raw")
    with pytest.raises(StorageError):
        db.initialize()
    assert db.conn.execute("SELECT to_regclass('meta.schema_info')").fetchone()[0] is None


def test_upsert_stale_reactivation_and_null(db):
    db.initialize()
    first = db.merge(API, BLOCK, [row(), row("002.SZ")], STAMP)
    assert first.inserted == 2
    second = db.merge(API, BLOCK, [row(value=None)], STAMP + timedelta(days=1), reconcile=True)
    assert (second.changed, second.stale) == (1, 1)
    same = db.merge(API, BLOCK, [row(value=None)], STAMP + timedelta(days=2))
    assert same.unchanged == 1
    updated = db.conn.execute(
        "SELECT _updated_at FROM raw.daily_basic WHERE ts_code='001.SZ'"
    ).fetchone()[0]
    assert updated == STAMP + timedelta(days=1)
    third = db.merge(API, BLOCK, [row("002.SZ", "2")], STAMP + timedelta(days=3))
    assert third.reactivated == 1
    assert db.counts(API) == (2, 0)


def test_failure_atomicity_and_success_age(db):
    db.initialize()
    db.merge(API, BLOCK, [row()], STAMP)
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.merge(API, BLOCK, [row(value="2"), row(value="3")], STAMP + timedelta(days=1))
    assert db.conn.execute("SELECT close FROM raw.daily_basic").fetchone()[0] == Decimal("1")
    db.failed(API, BLOCK, STAMP + timedelta(days=1))
    obs = db.observation(API, BLOCK)
    assert obs.failed and obs.last_success_at == STAMP
    assert db.counts(API) == (1, 0)


def test_empty_and_cross_scope_protection(db):
    db.initialize()
    db.merge(API, BLOCK, [row()], STAMP)
    empty = db.merge(API, BLOCK, [], STAMP + timedelta(days=1), reconcile=True)
    assert empty.stale == 0 and db.counts(API) == (1, 0)
    assert db.observation(API, BLOCK).last_reconciled_at is None
    with pytest.raises(StorageError):
        db.merge(API, BLOCK, [row(day=DAY + timedelta(days=1))], STAMP)
    assert db.counts(API) == (1, 0)


def test_snapshot_merge(db):
    db.initialize()
    api = replace(get_api("stock_basic"), stale_scope_verified=True)
    rows = [("001.SZ", *[None for _ in api.fields[1:]])]
    assert db.merge(api, BLOCK, rows, STAMP, reconcile=True).inserted == 1


def test_writer_lock(db):
    db.initialize()
    with psycopg.connect(db.conn.info.dsn, autocommit=True) as other:
        with db.writer():
            with pytest.raises(BusyError), Store(other).writer():
                pass
        with Store(other).writer():
            pass


def test_clean_confirmation_and_foreign_key(db):
    identity = db.initialize()
    db.merge(API, BLOCK, [row()], STAMP)
    assert db.clean(API)["active"] == 1
    with pytest.raises(StorageError):
        db.clean(API, apply=True, database="tushare", database_id=identity)
    db.conn.execute(
        "CREATE TABLE public.dependent (ts_code text, trade_date date, FOREIGN KEY(ts_code,trade_date) REFERENCES raw.daily_basic)"
    )
    try:
        db.conn.execute("INSERT INTO public.dependent VALUES ('001.SZ', '2024-01-02')")
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            db.clean(API, apply=True, database="tushare_test", database_id=identity)
        assert db.counts(API) == (1, 0)
    finally:
        db.conn.execute("DROP TABLE public.dependent")
    db.clean(API, apply=True, database="tushare_test", database_id=identity)
    assert db.counts(API) == (0, 0)
    assert db.observation(API, BLOCK) is None
