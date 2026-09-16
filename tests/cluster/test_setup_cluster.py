"""Opt-in destructive tests confined to an explicitly identified disposable cluster."""

import os
from dataclasses import replace
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

from tushare_downloader.config import Settings
from tushare_downloader.setup_db import apply_step, build_plan, snapshot, verify


@pytest.fixture
def cluster():
    dsn = os.environ.get("SETUP_TEST_ADMIN_URL")
    expected = os.environ.get("SETUP_TEST_DATA_DIRECTORY")
    if not dsn or not expected:
        pytest.fail("Setup tests require explicit disposable cluster URL and data directory.")
    conn = psycopg.connect(dsn, autocommit=True)
    actual = conn.execute("SHOW data_directory").fetchone()[0]
    if (
        actual.replace("\\", "/").lower() != expected.replace("\\", "/").lower()
        or conn.info.dbname != "postgres"
    ):
        conn.close()
        pytest.fail("Disposable cluster identity mismatch; no mutations permitted.")
    prefix = "tdw_" + uuid4().hex[:12]
    cfg = Settings(
        pg_host=conn.info.host, pg_port=conn.info.port, pg_database=prefix, pg_user=prefix + "_w"
    )
    admin = replace(cfg, pg_database="postgres", pg_user=conn.info.user)
    reader = prefix + "_r"
    try:
        yield cfg, admin, reader, conn
    finally:
        owner = conn.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (prefix,)
        ).fetchone()
        if owner:
            assert owner[0] == cfg.pg_user, "Unexpected owner; refusing cleanup"
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(prefix)))
        for role in [reader, cfg.pg_user]:
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
        conn.close()


def test_full_setup_and_reader_permissions(cluster):
    cfg, admin, reader, _ = cluster
    facts = snapshot(cfg, admin, reader)
    assert facts["kind"] == "missing"
    plan = build_plan(facts)
    for action in plan:
        facts = apply_step(facts, action, cfg, admin, reader)
    assert build_plan(facts) == []
    assert verify(cfg)["user"] == cfg.pg_user
    read_cfg = replace(cfg, pg_user=reader)
    assert verify(read_cfg)["user"] == reader
    with psycopg.connect(
        host=cfg.pg_host, port=cfg.pg_port, dbname=cfg.pg_database, user=reader, autocommit=True
    ) as conn:
        for statement in [
            "UPDATE raw.daily SET close=0 WHERE false",
            "DELETE FROM raw.daily WHERE false",
            "TRUNCATE raw.daily",
            "ALTER TABLE raw.daily ADD COLUMN unauthorized text",
            "CREATE TABLE raw.unauthorized(x int)",
        ]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)
    with psycopg.connect(
        host=cfg.pg_host,
        port=cfg.pg_port,
        dbname=cfg.pg_database,
        user=admin.pg_user,
        autocommit=True,
    ) as owner:
        owner.execute("CREATE SCHEMA analysis")
        owner.execute(
            "CREATE VIEW analysis.daily_active WITH (security_invoker=true) AS SELECT ts_code,trade_date FROM raw.daily WHERE NOT _is_stale"
        )
        owner.execute(
            sql.SQL("GRANT USAGE ON SCHEMA analysis TO {}").format(sql.Identifier(reader))
        )
        owner.execute(
            sql.SQL("GRANT SELECT ON analysis.daily_active TO {}").format(sql.Identifier(reader))
        )
    with psycopg.connect(
        host=cfg.pg_host, port=cfg.pg_port, dbname=cfg.pg_database, user=reader, autocommit=True
    ) as read:
        assert read.execute("SELECT * FROM analysis.daily_active").fetchall() == []
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            read.execute("DELETE FROM analysis.daily_active WHERE false")
    assert snapshot(cfg, admin, reader) == facts


def test_changed_state_refuses_old_plan(cluster):
    cfg, admin, reader, _ = cluster
    facts = snapshot(cfg, admin, reader)
    updated = apply_step(facts, "create-writer", cfg, admin, reader)
    from tushare_downloader.storage import StorageError

    with pytest.raises(StorageError, match="state changed"):
        apply_step(facts, "create-reader", cfg, admin, reader)
    assert "create-writer" not in build_plan(updated)


def test_export_contains_no_password_or_raw_ddl(cluster, tmp_path):
    from tushare_downloader.setup_export import export_bundle

    cfg, admin, reader, _ = cluster
    cfg = replace(cfg, pg_password="DO_NOT_PUBLISH_THIS")
    facts = snapshot(cfg, admin, reader)
    export_bundle(tmp_path / "bundle", facts, cfg, admin, reader, tmp_path / ".env")
    files = list((tmp_path / "bundle").iterdir())
    assert {p.name for p in files} == {
        "README.md",
        "01-admin.sql",
        "02-initialize.sh",
        "03-grants.sql",
        "04-reader-check.sql",
    }
    for path in files:
        assert "DO_NOT_PUBLISH_THIS" not in path.read_text()
        assert "CREATE TABLE" not in path.read_text()
        assert path.stat().st_mode & 0o777 == 0o600


def test_export_initialization_pins_target(cluster, tmp_path):
    from tushare_downloader.setup_export import export_bundle

    cfg, admin, reader, _ = cluster
    facts = snapshot(cfg, admin, reader)
    export_bundle(tmp_path / "bundle", facts, cfg, admin, reader, tmp_path / ".env")
    shell = (tmp_path / "bundle" / "02-initialize.sh").read_text()
    assert "PGDATABASE=" + cfg.pg_database in shell
    assert "PGUSER=" + cfg.pg_user in shell
    assert "PGHOST=" + cfg.pg_host in shell


def test_exported_steps_execute_with_planned_accounts(cluster, tmp_path):
    import subprocess
    from pathlib import Path

    from tushare_downloader.setup_export import export_bundle

    cfg, admin, reader, _ = cluster
    executable = os.environ.get("SETUP_TEST_PSQL")
    if not executable:
        pytest.fail("Set SETUP_TEST_PSQL to the psql binary for export verification.")
    facts = snapshot(cfg, admin, reader)
    # Reuse roles, so this unattended scenario does not need to automate password entry.
    for action in ["create-writer", "create-reader"]:
        facts = apply_step(facts, action, cfg, admin, reader)
    config = tmp_path / ".env"
    config.write_text(
        f"PGHOST={cfg.pg_host}\nPGPORT={cfg.pg_port}\nPGDATABASE={cfg.pg_database}\nPGUSER={cfg.pg_user}\n"
    )
    bundle = tmp_path / "bundle"
    export_bundle(bundle, facts, cfg, admin, reader, config)

    def run_sql(file, user, database):
        result = subprocess.run(
            [
                executable,
                "-X",
                "-h",
                cfg.pg_host,
                "-p",
                str(cfg.pg_port),
                "-U",
                user,
                "-d",
                database,
                "-f",
                "-",
            ],
            input=(bundle / file).read_text(),
            text=True,
            capture_output=True,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr

    run_sql("01-admin.sql", admin.pg_user, admin.pg_database)
    environment = dict(os.environ)
    environment["PATH"] = str(Path.cwd() / ".venv/bin") + os.pathsep + environment["PATH"]
    environment["PGDATABASE"] = "wrong_target_must_not_be_used"
    result = subprocess.run(
        ["bash", str(bundle / "02-initialize.sh")],
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    run_sql("03-grants.sql", admin.pg_user, cfg.pg_database)
    run_sql("04-reader-check.sql", reader, cfg.pg_database)
    assert build_plan(snapshot(cfg, admin, reader)) == []


def test_headless_fresh_target_check_apply_and_repeat(cluster, tmp_path, monkeypatch):
    import json

    from click.testing import CliRunner

    from tushare_downloader.cli import main

    cfg, admin, reader, conn = cluster
    monkeypatch.chdir(tmp_path)
    for key in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "SETUP_READER_USER"):
        monkeypatch.delenv(key, raising=False)
    config = tmp_path / ".env"
    config.write_text(
        f"PGHOST={cfg.pg_host}\nPGPORT={cfg.pg_port}\nPGDATABASE={cfg.pg_database}\n"
        f"PGUSER={cfg.pg_user}\nSETUP_READER_USER={reader}\n"
    )
    original = config.read_bytes()
    credentials = tmp_path / "private.json"
    credentials.write_text(
        json.dumps(
            {
                "version": 1,
                "admin": {"user": admin.pg_user},
                "writer": {"password": "fixture_writer_password"},
                "reader": {"password": "fixture_reader_password"},
            }
        )
    )
    credentials.chmod(0o600)
    args = ["setup", "--headless", "--credentials-file", str(credentials)]
    checked = CliRunner().invoke(main, args)
    assert checked.exit_code == 4, checked.output
    assert not conn.execute(
        "SELECT 1 FROM pg_database WHERE datname=%s", (cfg.pg_database,)
    ).fetchone()
    applied = CliRunner().invoke(main, args + ["--apply"])
    assert applied.exit_code == 0, applied.output
    assert config.read_bytes() == original
    state = snapshot(cfg, admin, reader)
    assert build_plan(state) == []
    repeated = CliRunner().invoke(main, ["setup", "--headless", "--apply"])
    assert repeated.exit_code == 0, repeated.output
    assert snapshot(cfg, admin, reader) == state
    assert "Applying:" not in repeated.output
    for log in (tmp_path / "logs/setup").glob("*.jsonl"):
        assert "fixture_writer_password" not in log.read_text()
        assert "fixture_reader_password" not in log.read_text()


def test_service_creates_new_database_with_existing_accounts(cluster, tmp_path):
    from tushare_downloader.setup_service import SetupSession

    cfg, admin, reader, _ = cluster
    state = snapshot(cfg, admin, reader)
    for action in ("create-writer", "create-reader"):
        state = apply_step(state, action, cfg, admin, reader)
    session = SetupSession(
        replace(cfg, log_dir=tmp_path), reader, {"admin": {"user": admin.pg_user}}
    )
    try:
        assert session.inspect()["readiness"] == "needs_configuration"
        result = session.apply()
        assert result["exit_code"] == 0, result
        assert result["completed"] == ["create-database", "initialize", "grants"]
    finally:
        session.close()
