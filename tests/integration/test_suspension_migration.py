"""Exercise the explicit migration against a real, disposable PostgreSQL database."""

import pytest
from click.testing import CliRunner

from tushare_downloader.cli import main
from tushare_downloader.config import Settings


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


def invoke(db, monkeypatch, tmp_path, *args):
    info = db.conn.info
    monkeypatch.setattr(
        "tushare_downloader.cli.settings",
        lambda ctx: Settings(
            pg_host=info.host,
            pg_port=info.port,
            pg_user=info.user,
            pg_database=info.dbname,
            log_dir=tmp_path,
        ),
    )
    return CliRunner().invoke(main, ["--plain", "migrate", "suspend_d", *args])


def test_preview_apply_repeat_preserves_table_and_rows(db, monkeypatch, tmp_path):
    old_database(db)
    oid = db.conn.execute("SELECT 'raw.suspend_d'::regclass::oid").fetchone()
    original = db.conn.execute("SELECT * FROM raw.suspend_d").fetchall()
    identity = db.identity()[0]
    result = invoke(db, monkeypatch, tmp_path)
    assert result.exit_code == 0, result.output
    assert db.identity()[1]["suspend_d"] == "1"
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
    assert result.exit_code == 0, result.output
    assert db.identity()[0] == identity
    assert db.identity()[1]["suspend_d"] == "2"
    assert db.conn.execute("SELECT 'raw.suspend_d'::regclass::oid").fetchone() == oid
    assert db.conn.execute("SELECT * FROM raw.suspend_d").fetchall() == original
    assert (
        invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test").exit_code
        == 0
    )


@pytest.mark.parametrize("kind", [None, "", " \t"])
def test_ambiguous_old_type_rejected_without_mutation(db, monkeypatch, tmp_path, kind):
    old_database(db, kind)
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
    assert result.exit_code == 1, result.output
    assert db.identity()[1]["suspend_d"] == "1"
    assert db.conn.execute("SELECT suspend_type FROM raw.suspend_d").fetchone() == (kind,)


def test_wrong_confirmation_never_changes_database(db, monkeypatch, tmp_path):
    old_database(db)
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "wrong")
    assert result.exit_code == 2, result.output
    assert db.identity()[1]["suspend_d"] == "1"


def test_foreign_key_blocks_but_ordinary_view_survives(db, monkeypatch, tmp_path):
    old_database(db)
    db.conn.execute(
        "CREATE VIEW public.r5_view AS SELECT ts_code,trade_date,suspend_type FROM raw.suspend_d"
    )
    db.conn.execute(
        "CREATE TABLE public.r5_dependency (code text, day date, FOREIGN KEY(code,day) REFERENCES raw.suspend_d(ts_code,trade_date))"
    )
    try:
        assert (
            invoke(
                db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test"
            ).exit_code
            == 1
        )
        assert db.identity()[1]["suspend_d"] == "1"
        db.conn.execute("DROP TABLE public.r5_dependency")
        assert (
            invoke(
                db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test"
            ).exit_code
            == 0
        )
        assert db.conn.execute("SELECT suspend_type FROM public.r5_view").fetchone() == ("S",)
    finally:
        db.conn.execute("DROP TABLE IF EXISTS public.r5_dependency")
        db.conn.execute("DROP VIEW public.r5_view")


def test_metadata_write_failure_rolls_back_ddl(db, monkeypatch, tmp_path):
    old_database(db)
    db.conn.execute(
        "ALTER TABLE meta.schema_info ADD CONSTRAINT r5_reject CHECK (specs->>'suspend_d' = '1')"
    )
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
    assert result.exit_code == 1
    assert db.identity()[1]["suspend_d"] == "1"
    from tushare_downloader.migration import legacy_suspension

    assert legacy_suspension(db)


def test_inspect_reports_known_old_contract_without_claiming_ready(db, monkeypatch, tmp_path):
    old_database(db)
    from tushare_downloader.inspection import inspect_dataset

    info = db.conn.info
    settings = Settings(
        pg_host=info.host, pg_port=info.port, pg_user=info.user, pg_database=info.dbname
    )
    result = inspect_dataset(settings, "suspend_d")
    assert result["State"] == "Migration needed"
    assert result["Installed schema"] == "1.0.0"
    assert result["Expected schema"] == "2.0.0"
    assert not result["ok"]


def test_writer_lock_and_missing_confirmation_are_safe(db, monkeypatch, tmp_path):
    import psycopg

    from tushare_downloader.storage import LOCK_KEY

    old_database(db)
    missing = invoke(db, monkeypatch, tmp_path, "--apply")
    assert missing.exit_code == 2
    with psycopg.connect(db.test_dsn, autocommit=True) as other:
        other.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
        busy = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
        assert busy.exit_code == 3
    assert db.identity()[1]["suspend_d"] == "1"


def test_old_observation_is_not_reused_after_migration(db, monkeypatch, tmp_path):
    from datetime import UTC, date, datetime

    from tushare_downloader.apis import get_api
    from tushare_downloader.planning import Block

    old_database(db)
    api = get_api("suspend_d")
    day = date(2026, 1, 12)
    stamp = datetime.now(UTC)
    block = Block((day - api.block_origin).days, day, day, day, day)
    db.conn.execute(
        "INSERT INTO meta.slices (api,block_id,spec_version,requested_start,requested_end,last_attempt_at,outcome,last_success_at,last_result_kind,local_active_count,local_stale_count) VALUES ('suspend_d',%s,'1',%s,%s,%s,'success',%s,'nonempty',1,0)",
        (block.id, day, day, stamp, stamp),
    )
    before = db.conn.execute("SELECT * FROM meta.slices").fetchall()
    assert (
        invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test").exit_code
        == 0
    )
    assert db.conn.execute("SELECT * FROM meta.slices").fetchall() == before
    assert db.observation(api, block).spec_version != api.spec_version


def test_migration_interrupt_is_130_and_does_not_change_rows(db, monkeypatch, tmp_path):
    import json

    old_database(db)

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr("tushare_downloader.migration.apply", interrupt)
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
    assert result.exit_code == 130
    assert db.identity()[1]["suspend_d"] == "1"
    events = [
        json.loads(line)
        for line in next((tmp_path / "migrate").glob("*.jsonl")).read_text().splitlines()
    ]
    assert events[-1]["exit_code"] == 130


def test_commit_acknowledgement_loss_is_not_replayed(db, monkeypatch, tmp_path):
    import psycopg

    from tushare_downloader import migration

    old_database(db)
    original_apply = migration.apply

    class LostAcknowledgement:
        def __init__(self, conn):
            self.conn = conn

        def __getattr__(self, name):
            return getattr(self.conn, name)

        def execute(self, statement, params=None):
            result = self.conn.execute(statement, params)
            if statement == "COMMIT":
                raise psycopg.OperationalError("synthetic acknowledgement loss")
            return result

    monkeypatch.setattr(
        migration,
        "apply",
        lambda conn, identity: original_apply(LostAcknowledgement(conn), identity),
    )
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
    assert result.exit_code == 1
    assert "Unknown" in result.output
    assert db.identity()[1]["suspend_d"] == "2"
    monkeypatch.setattr(migration, "apply", original_apply)
    repeated = invoke(db, monkeypatch, tmp_path)
    assert repeated.exit_code == 0 and "Already migrated" in repeated.output


def test_ddl_lock_wait_is_bounded(db, monkeypatch, tmp_path):
    from time import monotonic

    import psycopg

    old_database(db)
    with psycopg.connect(db.test_dsn) as other:
        other.execute("LOCK TABLE raw.suspend_d IN ACCESS EXCLUSIVE MODE")
        started = monotonic()
        result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
        assert result.exit_code == 1
        assert monotonic() - started < 9
    assert db.identity()[1]["suspend_d"] == "1"


def test_log_creation_failure_stops_before_database_change(db, monkeypatch, tmp_path):
    old_database(db)
    (tmp_path / "migrate").write_text("not a directory")
    result = invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test")
    assert result.exit_code == 1
    assert db.identity()[1]["suspend_d"] == "1"


def test_statement_budget_and_changed_structure_are_checked(db, monkeypatch, tmp_path):
    from tushare_downloader import migration

    old_database(db)
    original = migration.preflight

    def checked(store):
        assert store.conn.execute("SHOW statement_timeout").fetchone() == ("1min",)
        return original(store)

    monkeypatch.setattr(migration, "preflight", checked)
    assert invoke(db, monkeypatch, tmp_path).exit_code == 0
    db.conn.execute("ALTER TABLE raw.suspend_d ADD COLUMN unexpected text")
    assert (
        invoke(db, monkeypatch, tmp_path, "--apply", "--confirm-database", "tushare_test").exit_code
        == 1
    )
    assert db.identity()[1]["suspend_d"] == "1"
