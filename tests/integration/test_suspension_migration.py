"""MG06 storage invariants; setup authorization is tested through its public entry."""

from time import monotonic

import psycopg
import pytest

from tushare_downloader.migration import apply, legacy_suspension, preview
from tushare_downloader.migration_runtime import DeadlineConnection
from tushare_downloader.storage import BusyError, CommitUnknown, StorageError


def old_database(db, kind="S"):
    db.initialize()
    db.conn.execute("ALTER TABLE raw.suspend_d DROP CONSTRAINT suspend_d_pkey")
    db.conn.execute("ALTER TABLE raw.suspend_d ADD PRIMARY KEY (ts_code, trade_date)")
    db.conn.execute("ALTER TABLE raw.suspend_d ALTER COLUMN suspend_type DROP NOT NULL")
    db.conn.execute("UPDATE meta.schema_info SET specs=jsonb_set(specs,'{suspend_d}','\"1\"')")
    db.conn.execute(
        "INSERT INTO raw.suspend_d VALUES ('TEST.SH','2026-01-12',NULL,%s,false,NULL,now(),now())",
        (kind,),
    )


def migrate(db, connection=None):
    conn = DeadlineConnection(connection or db.conn, monotonic() + 60)
    return apply(conn, str(db.identity()[0]))


def test_preview_apply_repeat_preserves_table_and_rows(db):
    old_database(db)
    before = db.conn.execute("SELECT * FROM raw.suspend_d").fetchall()
    oid = db.conn.execute("SELECT 'raw.suspend_d'::regclass::oid").fetchone()
    identity = db.identity()[0]
    assert preview(db.conn)["spec"] == "1"
    assert migrate(db)["spec"] == "2"
    assert migrate(db)["state"] == "Already migrated"
    assert db.identity()[0] == identity
    assert db.conn.execute("SELECT * FROM raw.suspend_d").fetchall() == before
    assert db.conn.execute("SELECT 'raw.suspend_d'::regclass::oid").fetchone() == oid


@pytest.mark.parametrize("kind", [None, "", " \t"])
def test_ambiguous_type_rejected(db, kind):
    old_database(db, kind)
    with pytest.raises(StorageError, match="blank"):
        migrate(db)
    assert legacy_suspension(db)
    assert db.conn.execute("SELECT suspend_type FROM raw.suspend_d").fetchone() == (kind,)


def test_foreign_key_blocked_and_ordinary_view_preserved(db):
    old_database(db)
    db.conn.execute(
        "CREATE VIEW public.r6_view AS SELECT ts_code,trade_date,suspend_type FROM raw.suspend_d"
    )
    db.conn.execute(
        "CREATE TABLE public.r6_fk (code text, day date, FOREIGN KEY(code,day) REFERENCES raw.suspend_d(ts_code,trade_date))"
    )
    try:
        with pytest.raises(StorageError, match="foreign key"):
            migrate(db)
        assert legacy_suspension(db)
        db.conn.execute("DROP TABLE public.r6_fk")
        migrate(db)
        assert db.conn.execute("SELECT suspend_type FROM public.r6_view").fetchone() == ("S",)
    finally:
        db.conn.execute("DROP TABLE IF EXISTS public.r6_fk")
        db.conn.execute("DROP VIEW public.r6_view")


def test_metadata_failure_rolls_back_structure(db):
    old_database(db)
    db.conn.execute(
        "ALTER TABLE meta.schema_info ADD CONSTRAINT reject_new CHECK (specs->>'suspend_d' = '1')"
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        migrate(db)
    assert legacy_suspension(db)


def test_lock_conflict_and_ddl_wait_bounded(db):
    from tushare_downloader.storage import LOCK_KEY

    old_database(db)
    with psycopg.connect(db.test_dsn, autocommit=True) as other:
        other.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
        with pytest.raises(BusyError):
            migrate(db)
    with psycopg.connect(db.test_dsn) as other:
        other.execute("LOCK TABLE raw.suspend_d IN ACCESS EXCLUSIVE MODE")
        started = monotonic()
        with pytest.raises(psycopg.errors.LockNotAvailable):
            migrate(db)
        assert monotonic() - started < 9
    assert legacy_suspension(db)


def test_commit_loss_is_unknown_but_not_replayed(db):
    old_database(db)

    class LostCommit:
        def __getattr__(self, name):
            return getattr(db.conn, name)

        def execute(self, statement, params=None):
            result = db.conn.execute(statement, params)
            if statement == "COMMIT":
                raise psycopg.OperationalError("Injected lost response")
            return result

    with pytest.raises(CommitUnknown):
        migrate(db, LostCommit())
    assert db.identity()[1]["suspend_d"] == "2"
    assert preview(db.conn)["state"] == "Already migrated"


def test_changed_structure_and_statement_budget(db):
    old_database(db)
    conn = DeadlineConnection(db.conn, monotonic() + 1)
    with pytest.raises(psycopg.errors.QueryCanceled):
        conn.execute("SELECT pg_sleep(2)")
    db.conn.execute("ALTER TABLE raw.suspend_d ADD COLUMN unexpected text")
    with pytest.raises(StorageError):
        migrate(db)
    assert db.identity()[1]["suspend_d"] == "1"


def test_old_observation_survives_and_is_not_reused(db):
    from datetime import UTC, date, datetime

    from tushare_downloader.apis import get_api
    from tushare_downloader.planning import Block

    old_database(db)
    api = get_api("suspend_d")
    day = date(2026, 1, 12)
    block = Block((day - api.block_origin).days, day, day, day, day)
    stamp = datetime.now(UTC)
    db.conn.execute(
        "INSERT INTO meta.slices (api,block_id,spec_version,requested_start,requested_end,last_attempt_at,outcome,last_success_at,last_result_kind,local_active_count,local_stale_count) VALUES ('suspend_d',%s,'1',%s,%s,%s,'success',%s,'nonempty',1,0)",
        (block.id, day, day, stamp, stamp),
    )
    before = db.conn.execute("SELECT * FROM meta.slices").fetchall()
    migrate(db)
    assert db.conn.execute("SELECT * FROM meta.slices").fetchall() == before
    assert db.observation(api, block).spec_version != api.spec_version
