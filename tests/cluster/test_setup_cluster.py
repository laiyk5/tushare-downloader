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


@pytest.mark.parametrize("password_suffix", ["", "'\\<>&;--"])
def test_real_scram_failure_recovers_without_replaying_mutations(
    cluster, tmp_path, password_suffix
):
    import time
    from pathlib import Path

    from tushare_downloader.setup_service import DatabaseBackend, SetupSession

    cfg, admin, reader, conn = cluster
    writer_secret = "fixture_writer_scram" + password_suffix
    initial_reader_secret = "fixture_initial_reader" + password_suffix
    corrected_reader_secret = "fixture_corrected_reader" + password_suffix
    hba_name = conn.execute("SHOW hba_file").fetchone()[0].replace("\\", "/")
    expected = os.environ["SETUP_TEST_DATA_DIRECTORY"].replace("\\", "/").rstrip("/")
    assert hba_name.lower() == (expected + "/pg_hba.conf").lower()
    if len(hba_name) > 2 and hba_name[1] == ":":
        hba_name = "/mnt/" + hba_name[0].lower() + hba_name[2:]
    hba = Path(hba_name)
    original = hba.read_bytes()

    def reload_rules():
        previous = conn.execute("SELECT pg_conf_load_time()").fetchone()[0]
        assert conn.execute("SELECT pg_reload_conf()").fetchone()[0]
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if conn.execute("SELECT pg_conf_load_time()").fetchone()[0] > previous:
                return
            time.sleep(0.02)
        pytest.fail("Isolated authentication reload did not complete")

    class ChangedCredential(DatabaseBackend):
        def __init__(self):
            super().__init__()
            self.writes = []

        def apply(self, expected_state, action, *args):
            result = super().apply(expected_state, action, *args)
            self.writes.append(action)
            if action == "grants":
                conn.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(reader), sql.Literal(corrected_reader_secret)
                    )
                )
            return result

    backend = ChangedCredential()
    session = None
    try:
        rules = (
            f"host all {cfg.pg_user},{reader} 127.0.0.1/32 scram-sha-256\n"
            f"host all {cfg.pg_user},{reader} ::1/128 scram-sha-256\n"
        )
        hba.write_bytes(rules.encode() + original)
        reload_rules()
        session = SetupSession(
            replace(cfg, log_dir=tmp_path),
            reader,
            {
                "admin": {"user": admin.pg_user},
                "writer": {"password": writer_secret},
                "reader": {"password": initial_reader_secret},
            },
            backend=backend,
        )
        session.inspect()
        failed = session.apply()
        assert failed["exit_code"] == 1, failed
        assert failed["reason_code"] == "verification_failed"
        assert failed["writer_verification"] == "verified"
        assert failed["reader_verification"] == "failed"
        assert failed["completed"] == [
            "create-writer",
            "create-reader",
            "create-database",
            "initialize",
            "grants",
        ]
        writes = list(backend.writes)
        for bad in ("", "incorrect"):
            rejected = session.retry_verification(reader_password=bad)
            assert rejected["exit_code"] == 1
            assert backend.writes == writes
        verified = session.retry_verification(reader_password=corrected_reader_secret)
        assert verified["exit_code"] == 0, verified
        assert verified["reader_verification"] == "verified"
        assert verified["completed"] == failed["completed"]
        assert backend.writes == writes
        assert corrected_reader_secret not in session.log.path.read_text()

        # Existing roles: missing/wrong credentials must be caught before grants.
        with psycopg.connect(
            host=cfg.pg_host,
            port=cfg.pg_port,
            dbname=cfg.pg_database,
            user=admin.pg_user,
            autocommit=True,
        ) as owner:
            owner.execute(
                sql.SQL("REVOKE SELECT ON raw.daily FROM {}").format(sql.Identifier(reader))
            )
        before_repair = snapshot(cfg, admin, reader)
        assert build_plan(before_repair) == ["grants"]
        password_state = conn.execute(
            "SELECT rolname,rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
            (cfg.pg_user, reader),
        ).fetchall()

        class TrackWrites(DatabaseBackend):
            def __init__(self):
                super().__init__()
                self.writes = []

            def apply(self, expected_state, action, *args):
                self.writes.append(action)
                return super().apply(expected_state, action, *args)

        for bad in ("", "incorrect"):
            tracked = TrackWrites()
            attempt = SetupSession(
                replace(cfg, log_dir=tmp_path, pg_password=writer_secret),
                reader,
                {"admin": {"user": admin.pg_user}, "reader": {"password": bad}},
                backend=tracked,
            )
            try:
                assert attempt.inspect()["actions"] == ["grants"]
                rejected = attempt.apply()
                assert rejected["exit_code"] == 1
                assert rejected["completed"] == []
                assert rejected["not_attempted"] == ["grants"]
                assert tracked.writes == []
                assert snapshot(cfg, admin, reader) == before_repair
            finally:
                attempt.close()

            tracked = TrackWrites()
            wrong_writer = SetupSession(
                replace(cfg, log_dir=tmp_path, pg_password=bad),
                reader,
                {
                    "admin": {"user": admin.pg_user},
                    "reader": {"password": corrected_reader_secret},
                },
                backend=tracked,
            )
            try:
                assert wrong_writer.inspect()["readiness"] == "unknown"
                assert wrong_writer.apply()["exit_code"] == 1
                assert tracked.writes == []
            finally:
                wrong_writer.close()

        tracked = TrackWrites()
        repair = SetupSession(
            replace(cfg, log_dir=tmp_path, pg_password=writer_secret),
            reader,
            {"admin": {"user": admin.pg_user}, "reader": {"password": corrected_reader_secret}},
            backend=tracked,
        )
        try:
            assert repair.inspect()["actions"] == ["grants"]
            repaired = repair.apply()
            assert repaired["exit_code"] == 0
            assert tracked.writes == ["grants"]
            assert repaired["writer_verification"] == "verified"
            assert repaired["reader_verification"] == "verified"
        finally:
            repair.close()
        assert (
            conn.execute(
                "SELECT rolname,rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                (cfg.pg_user, reader),
            ).fetchall()
            == password_state
        )
    finally:
        if session:
            session.close()
        hba.write_bytes(original)
        reload_rules()


def test_missing_reader_connect_is_repaired_without_changing_public(cluster):
    cfg, admin, reader, conn = cluster
    facts = snapshot(cfg, admin, reader)
    for action in build_plan(facts):
        facts = apply_step(facts, action, cfg, admin, reader)
    assert build_plan(facts) == []
    # Only this randomly named disposable database is affected.
    conn.execute(
        sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC, {}").format(
            sql.Identifier(cfg.pg_database), sql.Identifier(reader)
        )
    )
    facts = snapshot(cfg, admin, reader)
    assert build_plan(facts) == ["grants"]
    repaired = apply_step(facts, "grants", cfg, admin, reader)
    assert build_plan(repaired) == []
    assert conn.execute(
        "SELECT has_database_privilege(%s,%s,'CONNECT')", (reader, cfg.pg_database)
    ).fetchone()[0]
    assert not conn.execute(
        "SELECT EXISTS (SELECT 1 FROM pg_database d, LATERAL aclexplode(d.datacl) a "
        "WHERE d.datname=%s AND a.grantee=0 AND a.privilege_type='CONNECT')",
        (cfg.pg_database,),
    ).fetchone()[0]


def test_ready_performance_and_sql_scope_empty_and_100k(cluster, tmp_path, monkeypatch):
    import json
    import platform
    import re
    import time
    from pathlib import Path

    from tushare_downloader import setup_db, setup_service
    from tushare_downloader.apis import APIS

    cfg, admin, reader, conn = cluster
    facts = snapshot(cfg, admin, reader)
    for action in build_plan(facts):
        facts = apply_step(facts, action, cfg, admin, reader)
    assert len(APIS) == 6
    cfg = replace(cfg, log_dir=tmp_path)
    original_connect = setup_db.connect
    queries = []

    class TracedConnection:
        def __init__(self, config):
            self.connection = original_connect(config)

        def __enter__(self):
            self.connection.__enter__()
            return self

        def __exit__(self, *args):
            return self.connection.__exit__(*args)

        def __getattr__(self, key):
            return getattr(self.connection, key)

        def execute(self, query, *args, **kwargs):
            queries.append(query if isinstance(query, str) else query.as_string(self.connection))
            return self.connection.execute(query, *args, **kwargs)

    def state():
        # Fixture-only snapshots, outside the measured/traced inspection.
        with original_connect(cfg) as target:
            return {
                "identity": target.execute("SELECT * FROM meta.schema_info").fetchall(),
                "objects": target.execute(
                    "SELECT n.nspname,c.relname,c.relowner,c.relacl FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('raw','meta') ORDER BY 1,2"
                ).fetchall(),
            }

    evidence = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "postgresql": conn.execute("SELECT version()").fetchone()[0],
        "samples": [],
    }
    for rows in (0, 100000):
        if rows:
            with original_connect(cfg) as target:
                target.execute(
                    "INSERT INTO raw.daily(ts_code,trade_date,_is_stale,_last_seen_at,_updated_at) "
                    "SELECT 'fixture', DATE '1900-01-01'+i, false, now(), now() "
                    "FROM generate_series(0,99999) AS i"
                )
        before = state()
        queries.clear()
        with monkeypatch.context() as patch:
            patch.setattr(setup_db, "connect", TracedConnection)
            patch.setattr(setup_service, "connect", TracedConnection)
            checked = setup_service._inspect(cfg, admin, reader)
            assert build_plan(checked) == []
        assert queries
        for query in queries:
            assert re.match(r"\s*SELECT\b", query, re.I), query
            assert not re.search(r"\b(?:FROM|JOIN)\s+\"?raw\"?\s*\.", query, re.I), query
        assert state() == before
        credentials = {"admin": {"user": admin.pg_user}}
        service = setup_service.SetupSession(cfg, reader, credentials)
        try:
            assert service.inspect()["readiness"] == "ready"  # warm-up
            elapsed = []
            for _ in range(10):
                start = time.monotonic()
                assert service.inspect()["readiness"] == "ready"
                elapsed.append(time.monotonic() - start)
            p95 = sorted(elapsed)[9]  # nearest rank for ten samples
            assert p95 <= 2, elapsed
        finally:
            service.close()
        assert state() == before
        evidence["samples"].append(
            {
                "rows": rows,
                "seconds": elapsed,
                "p95_seconds": p95,
                "database_bytes": conn.execute(
                    "SELECT pg_database_size(%s)", (cfg.pg_database,)
                ).fetchone()[0],
                "queries": list(queries),
            }
        )
    output = os.environ.get("SETUP_PERF_EVIDENCE")
    if output:
        Path(output).write_text(json.dumps(evidence, indent=2) + "\n")


@pytest.mark.parametrize(
    "action", ["create-writer", "create-reader", "create-database", "initialize", "grants"]
)
@pytest.mark.parametrize("fault", ["rejected_before", "rejected", "acknowledgement_lost"])
def test_each_action_preserves_real_transaction_outcomes(
    cluster, tmp_path, monkeypatch, action, fault
):
    from tushare_downloader import setup_db
    from tushare_downloader.bounded import RemoteFailure, safe_error
    from tushare_downloader.setup_service import DatabaseBackend, SetupSession

    cfg, admin, reader, _ = cluster
    actions = ["create-writer", "create-reader", "create-database", "initialize", "grants"]
    index = actions.index(action)
    original_statements = setup_db.statements
    original_initialize = setup_db.Store.initialize

    def rejected_statements(selected, *args, **kwargs):
        statements = original_statements(selected, *args, **kwargs)
        if selected != action:
            return statements
        if selected == "create-database":
            # CREATE DATABASE is nontransactional: fail before it can create anything.
            return [
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(cfg.pg_database), sql.Identifier(cfg.pg_user + "_missing")
                )
            ]
        return statements + [sql.SQL("SELECT 1/0")]

    def rejected_initialize(store):
        # Store controls BEGIN/COMMIT itself: inject inside that transaction,
        # after its final metadata update but before its COMMIT.
        original = store.conn

        class FailBeforeCommit:
            def __getattr__(self, key):
                return getattr(original, key)

            def execute(self, statement, *args, **kwargs):
                result = original.execute(statement, *args, **kwargs)
                if isinstance(statement, str) and statement.startswith(
                    "UPDATE meta.schema_info SET specs="
                ):
                    original.execute("SELECT 1/0")
                return result

        store.conn = FailBeforeCommit()
        try:
            return original_initialize(store)
        finally:
            store.conn = original

    class FaultBackend(DatabaseBackend):
        def __init__(self):
            super().__init__()
            self.writes = []

        def apply(self, expected, selected, *args):
            self.writes.append(selected)
            if selected != action:
                return super().apply(expected, selected, *args)
            if fault == "rejected_before":
                raise RemoteFailure("Controlled pre-execution refusal", "StorageError", None)
            if fault == "acknowledgement_lost":
                super().apply(expected, selected, *args)
                raise RuntimeError("Simulated lost acknowledgement after confirmed server commit")
            with monkeypatch.context() as patch:
                patch.setattr(setup_db, "statements", rejected_statements)
                if selected == "initialize":
                    patch.setattr(setup_db.Store, "initialize", rejected_initialize)
                try:
                    return setup_db.apply_step(expected, selected, *args)
                except psycopg.Error as error:
                    raise RemoteFailure(
                        safe_error(error), type(error).__name__, error.sqlstate
                    ) from None

    backend = FaultBackend()
    credentials = {
        "admin": {"user": admin.pg_user},
        "writer": {"allow_passwordless_creation": True},
        "reader": {"allow_passwordless_creation": True},
    }
    service = SetupSession(replace(cfg, log_dir=tmp_path), reader, credentials, backend=backend)
    try:
        assert service.inspect()["actions"] == actions
        result = service.apply()
        assert result["exit_code"] == 1
        assert result["completed"] == actions[:index]
        assert result["failed"] == ([action] if fault != "acknowledgement_lost" else [])
        assert result["unknown"] == ([action] if fault == "acknowledgement_lost" else [])
        assert result["not_attempted"] == actions[index + 1 :]
        assert backend.writes == actions[: index + 1]
        actual = snapshot(cfg, admin, reader)
        assert (
            build_plan(actual) == actions[index + 1 if fault == "acknowledgement_lost" else index :]
        )
    finally:
        service.close()


def test_actual_v030_database_retains_identity_data_and_user_objects(cluster, tmp_path):
    import json
    import subprocess
    import sys
    from pathlib import Path

    from tushare_downloader.setup_service import DatabaseBackend, SetupSession

    cfg, admin, reader, conn = cluster
    repo = Path(__file__).resolve().parents[2]
    baseline_commit = subprocess.check_output(
        ["git", "rev-parse", "v0.3.0^{commit}"], cwd=repo, text=True
    ).strip()
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", baseline_commit, "src/tushare_downloader"],
        cwd=repo,
        text=True,
    ).splitlines()
    assert files
    baseline = tmp_path / "baseline"
    for filename in files:
        path = baseline / filename
        assert path.resolve().is_relative_to(baseline.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            subprocess.check_output(["git", "show", baseline_commit + ":" + filename], cwd=repo)
        )
    facts = snapshot(cfg, admin, reader)
    for action in ["create-writer", "create-reader", "create-database"]:
        facts = apply_step(facts, action, cfg, admin, reader)
    environment = dict(os.environ, PYTHONPATH=str(baseline / "src"))
    program = (
        "import json,sys; from tushare_downloader.config import Settings; "
        "from tushare_downloader.storage import Store,connect; "
        "cfg=Settings(**json.loads(sys.argv[1])); "
        "conn=connect(cfg); store=Store(conn); store.initialize(); conn.close()"
    )
    subprocess.run(
        [
            sys.executable,
            "-c",
            program,
            json.dumps(
                {
                    "pg_host": cfg.pg_host,
                    "pg_port": cfg.pg_port,
                    "pg_database": cfg.pg_database,
                    "pg_user": cfg.pg_user,
                }
            ),
        ],
        cwd=baseline,
        env=environment,
        check=True,
        timeout=20,
    )
    with psycopg.connect(
        host=cfg.pg_host,
        port=cfg.pg_port,
        dbname=cfg.pg_database,
        user=cfg.pg_user,
        autocommit=True,
    ) as target:
        target.execute(
            "INSERT INTO raw.daily(ts_code,trade_date,close,_is_stale,_last_seen_at,_updated_at) VALUES ('fixture','2026-01-05',123.45,false,now(),now())"
        )
        target.execute("CREATE SCHEMA analysis")
        target.execute("CREATE VIEW analysis.saved_daily AS SELECT ts_code,close FROM raw.daily")

        def preserved():
            return (
                target.execute("SELECT * FROM meta.schema_info").fetchall(),
                target.execute("SELECT * FROM raw.daily").fetchall(),
                target.execute(
                    "SELECT pg_get_viewdef('analysis.saved_daily'::regclass)"
                ).fetchone(),
                target.execute("SELECT * FROM analysis.saved_daily").fetchall(),
                conn.execute(
                    "SELECT rolname,rolpassword FROM pg_authid WHERE rolname IN (%s,%s) ORDER BY rolname",
                    (cfg.pg_user, reader),
                ).fetchall(),
            )

        before = preserved()

        class Recorded(DatabaseBackend):
            def __init__(self):
                super().__init__()
                self.writes = []

            def apply(self, expected, action, *args):
                self.writes.append(action)
                return super().apply(expected, action, *args)

        backend = Recorded()
        service = SetupSession(
            replace(cfg, log_dir=tmp_path),
            reader,
            {"admin": {"user": admin.pg_user}},
            backend=backend,
        )
        try:
            assert service.inspect()["actions"] == ["grants"]
            assert service.apply()["exit_code"] == 0
            assert preserved() == before
            assert service.inspect()["readiness"] == "ready"
            assert service.apply()["exit_code"] == 0
            assert backend.writes == ["grants"]
            assert preserved() == before
        finally:
            service.close()
    print("Verified actual baseline:", baseline_commit)


@pytest.mark.parametrize(
    "scenario",
    [
        "owned_empty",
        "foreign_empty",
        "external_object",
        "future_schema",
        "unsafe_reader",
        "inherited_writer",
        "reader_table_write",
        "reader_schema_create",
        "reader_security_definer",
        "inspection_denied",
        "column_drift",
        "schema_owner_drift",
    ],
)
def test_real_database_classification_never_repairs_unsupported_state(cluster, tmp_path, scenario):
    from tushare_downloader.setup_service import DatabaseBackend, SetupSession

    cfg, admin, reader, conn = cluster
    facts = snapshot(cfg, admin, reader)
    for action in ["create-writer", "create-reader", "create-database"]:
        facts = apply_step(facts, action, cfg, admin, reader)
    if scenario not in {"owned_empty", "foreign_empty", "external_object"}:
        for action in build_plan(facts):
            facts = apply_step(facts, action, cfg, admin, reader)
    target = psycopg.connect(
        host=cfg.pg_host,
        port=cfg.pg_port,
        dbname=cfg.pg_database,
        user=admin.pg_user,
        autocommit=True,
    )
    service = None
    try:
        if scenario == "foreign_empty":
            conn.execute(
                sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                    sql.Identifier(cfg.pg_database), sql.Identifier(admin.pg_user)
                )
            )
        elif scenario == "external_object":
            target.execute("CREATE TABLE public.unrelated(value text)")
            target.execute("INSERT INTO public.unrelated VALUES ('preserve')")
        elif scenario == "future_schema":
            target.execute("UPDATE meta.schema_info SET schema_version=999")
        elif scenario == "unsafe_reader":
            conn.execute(sql.SQL("ALTER ROLE {} CREATEDB").format(sql.Identifier(reader)))
        elif scenario == "column_drift":
            target.execute("ALTER TABLE raw.daily ALTER COLUMN close TYPE text")
        elif scenario == "schema_owner_drift":
            target.execute(
                sql.SQL("ALTER SCHEMA raw OWNER TO {}").format(sql.Identifier(admin.pg_user))
            )
        elif scenario == "inherited_writer":
            conn.execute(
                sql.SQL("GRANT {} TO {}").format(
                    sql.Identifier(cfg.pg_user), sql.Identifier(reader)
                )
            )
        elif scenario == "reader_table_write":
            target.execute(
                sql.SQL("GRANT UPDATE ON raw.daily TO {}").format(sql.Identifier(reader))
            )
        elif scenario == "reader_schema_create":
            target.execute(
                sql.SQL("GRANT CREATE ON SCHEMA raw TO {}").format(sql.Identifier(reader))
            )
        elif scenario == "reader_security_definer":
            target.execute(
                "CREATE FUNCTION public.fixture_definer() RETURNS integer LANGUAGE sql SECURITY DEFINER AS 'SELECT 1'"
            )
        elif scenario == "inspection_denied":
            target.execute(
                sql.SQL("REVOKE USAGE ON SCHEMA meta FROM {}").format(sql.Identifier(reader))
            )

        def objects():
            return target.execute(
                "SELECT n.nspname,c.relname,c.relowner,c.relacl FROM pg_class c "
                "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('raw','meta','public') ORDER BY 1,2"
            ).fetchall()

        before = objects()

        def privileges():
            return (
                conn.execute(
                    "SELECT roleid,member,admin_option,inherit_option,set_option FROM pg_auth_members ORDER BY 1,2"
                ).fetchall(),
                target.execute(
                    "SELECT nspname,nspowner,nspacl FROM pg_namespace WHERE nspname IN ('raw','meta','public') ORDER BY 1"
                ).fetchall(),
                target.execute(
                    "SELECT proname,proowner,prosecdef,proacl FROM pg_proc WHERE pronamespace='public'::regnamespace ORDER BY 1"
                ).fetchall(),
            )

        original_privileges = privileges()

        class NoWrite(DatabaseBackend):
            def apply(self, *args):
                raise AssertionError("Unsupported inspection must never write")

        service = SetupSession(
            replace(cfg, log_dir=tmp_path),
            reader,
            {"admin": {"user": reader if scenario == "inspection_denied" else admin.pg_user}},
            backend=NoWrite(),
        )
        checked = service.inspect()
        if scenario == "owned_empty":
            assert checked["readiness"] == "needs_configuration"
            assert checked["actions"] == ["initialize", "grants"]
        elif scenario == "inspection_denied":
            assert checked["readiness"] == "unknown", checked
            assert checked["actions"] == []
            assert service.apply()["exit_code"] == 1
        else:
            assert checked["readiness"] == "unsupported", checked
            assert checked["actions"] == []
            assert service.apply()["exit_code"] == 5
        assert objects() == before
        assert privileges() == original_privileges
        if scenario == "external_object":
            assert target.execute("SELECT * FROM public.unrelated").fetchall() == [("preserve",)]
        if scenario == "future_schema":
            assert target.execute("SELECT schema_version FROM meta.schema_info").fetchone() == (
                999,
            )
        if scenario == "unsafe_reader":
            assert conn.execute(
                "SELECT rolcreatedb FROM pg_roles WHERE rolname=%s", (reader,)
            ).fetchone() == (True,)
    finally:
        if service:
            service.close()
        target.close()
        if scenario == "inherited_writer":
            conn.execute(
                sql.SQL("REVOKE {} FROM {}").format(
                    sql.Identifier(cfg.pg_user), sql.Identifier(reader)
                )
            )
        if scenario == "foreign_empty":
            conn.execute(
                sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                    sql.Identifier(cfg.pg_database), sql.Identifier(cfg.pg_user)
                )
            )
        if scenario == "unsafe_reader":
            conn.execute(sql.SQL("ALTER ROLE {} NOCREATEDB").format(sql.Identifier(reader)))


def test_writer_alone_adds_missing_table_using_existing_reader_defaults(cluster, tmp_path):
    from tushare_downloader.setup_service import DatabaseBackend, SetupSession

    cfg, admin, reader, _ = cluster
    facts = snapshot(cfg, admin, reader)
    for action in build_plan(facts):
        facts = apply_step(facts, action, cfg, admin, reader)
    original_id = facts["database_id"]
    with psycopg.connect(
        host=cfg.pg_host,
        port=cfg.pg_port,
        dbname=cfg.pg_database,
        user=cfg.pg_user,
        autocommit=True,
    ) as target:
        target.execute(
            "INSERT INTO raw.daily(ts_code,trade_date,_is_stale,_last_seen_at,_updated_at) VALUES ('preserve','2026-01-05',false,now(),now())"
        )
        before = target.execute("SELECT * FROM raw.daily").fetchall()
        target.execute("DROP TABLE raw.adj_factor")
        target.execute("UPDATE meta.schema_info SET specs=specs-'adj_factor'")

        class WriterOnly(DatabaseBackend):
            def __init__(self):
                super().__init__()
                self.writes = []

            def inspect(self, selected, administrator, selected_reader):
                assert administrator.pg_user == cfg.pg_user
                return super().inspect(selected, administrator, selected_reader)

            def apply(self, expected, action, *args):
                self.writes.append(action)
                return super().apply(expected, action, *args)

            def verify(self, selected, reader_settings):
                assert reader_settings is None, "Adding a table must not require a reader login"
                return super().verify(selected, reader_settings)

        backend = WriterOnly()
        service = SetupSession(replace(cfg, log_dir=tmp_path), reader, {}, backend=backend)
        try:
            checked = service.inspect()
            assert checked["actions"] == ["initialize"]
            result = service.apply()
            assert result["exit_code"] == 0, result
            assert result["reader_verification"] == "not_checked"
            assert result["writer_verification"] == "verified"
            assert backend.writes == ["initialize"]
            actual = snapshot(cfg, cfg, reader)
            assert actual["database_id"] == original_id
            assert build_plan(actual) == []
            assert target.execute("SELECT * FROM raw.daily").fetchall() == before
            assert target.execute(
                "SELECT has_table_privilege(%s,'raw.adj_factor','SELECT')", (reader,)
            ).fetchone() == (True,)
        finally:
            service.close()


def _commit_then_hold_result(marker, expected, action, *args):
    """Simulate a stuck result channel after the real server has committed."""
    import time
    from pathlib import Path

    apply_step(expected, action, *args)
    Path(marker).touch()
    time.sleep(30)


@pytest.mark.parametrize(
    "action", ["create-writer", "create-reader", "create-database", "initialize", "grants"]
)
@pytest.mark.parametrize("fault", ["timeout", "cancel"])
def test_each_action_bounded_termination_preserves_commits(cluster, tmp_path, action, fault):
    import multiprocessing
    import time
    from threading import Event, Thread

    from tushare_downloader.bounded import bounded
    from tushare_downloader.setup_service import DatabaseBackend, SetupSession

    cfg, admin, reader, _ = cluster
    actions = ["create-writer", "create-reader", "create-database", "initialize", "grants"]
    index = actions.index(action)
    marker = tmp_path / "committed"
    stop = Event()
    cancelled = Event()

    class HeldBackend(DatabaseBackend):
        def __init__(self):
            super().__init__()
            self.writes = []
            self.elapsed = None

        def apply(self, expected, selected, *args):
            self.writes.append(selected)
            if selected != action:
                return super().apply(expected, selected, *args)
            started = time.monotonic()
            try:
                return bounded(
                    _commit_then_hold_result,
                    str(marker),
                    expected,
                    selected,
                    *args,
                    seconds=5,
                    cancel=cancelled,
                )
            finally:
                self.elapsed = time.monotonic() - started

    def cancel_after_commit():
        while not stop.wait(0.01):
            if marker.exists():
                cancelled.set()
                return

    backend = HeldBackend()
    credentials = {
        "admin": {"user": admin.pg_user},
        "writer": {"allow_passwordless_creation": True},
        "reader": {"allow_passwordless_creation": True},
    }
    service = SetupSession(replace(cfg, log_dir=tmp_path), reader, credentials, backend=backend)
    watcher = Thread(target=cancel_after_commit, daemon=True) if fault == "cancel" else None
    initial_children = {p.pid for p in multiprocessing.active_children()}
    try:
        assert service.inspect()["actions"] == actions
        if watcher:
            watcher.start()
        result = service.apply()
        assert marker.exists(), "The server commit must precede the injected interruption"
        assert result["exit_code"] == (130 if fault == "cancel" else 1)
        assert result["completed"] == actions[:index]
        assert result["failed"] == []
        assert result["unknown"] == [action]
        assert result["not_attempted"] == actions[index + 1 :]
        assert backend.writes == actions[: index + 1]
        assert backend.elapsed < 7  # five-second deadline plus termination allowance
        assert build_plan(snapshot(cfg, admin, reader)) == actions[index + 1 :]
        assert {p.pid for p in multiprocessing.active_children()} == initial_children
        # A user-requested fresh inspection derives only remaining operations.
        # It never replays the unacknowledged-but-committed action.
        before_retry = snapshot(cfg, admin, reader)
        assert service.inspect()["actions"] == actions[index + 1 :]
        retried = service.apply()
        assert retried["exit_code"] == 0
        assert retried["completed"] == actions[index + 1 :]
        assert backend.writes == actions
        after_retry = snapshot(cfg, admin, reader)
        assert build_plan(after_retry) == []
        if before_retry.get("database_id"):
            assert after_retry["database_id"] == before_retry["database_id"]
        assert service.inspect()["actions"] == []
        assert service.apply()["exit_code"] == 0
        assert backend.writes == actions
    finally:
        stop.set()
        if watcher:
            watcher.join(timeout=1)
        service.close()


def test_real_writer_lock_retains_prior_steps_and_allows_fresh_plan(cluster, tmp_path):
    import json

    from tushare_downloader.setup_service import DatabaseBackend, SetupSession
    from tushare_downloader.storage import Store, connect

    cfg, admin, reader, _ = cluster

    class LockedBackend(DatabaseBackend):
        armed = True

        def apply(self, expected, action, *args):
            if action == "initialize" and self.armed:
                self.armed = False
                with connect(cfg) as holder, Store(holder).writer():
                    return super().apply(expected, action, *args)
            return super().apply(expected, action, *args)

    credentials = {
        "admin": {"user": admin.pg_user},
        "writer": {"allow_passwordless_creation": True},
        "reader": {"allow_passwordless_creation": True},
    }
    service = SetupSession(
        replace(cfg, log_dir=tmp_path), reader, credentials, backend=LockedBackend()
    )
    try:
        service.inspect()
        result = service.apply()
        assert result["exit_code"] == 3
        assert result["completed"] == ["create-writer", "create-reader", "create-database"]
        assert result["failed"] == ["initialize"]
        assert result["unknown"] == []
        assert result["not_attempted"] == ["grants"]
        record = json.loads(service.log.path.read_text().splitlines()[-1])
        assert record["exit_code"] == 3
        assert record["completed"] == result["completed"]
        assert build_plan(snapshot(cfg, admin, reader)) == ["initialize", "grants"]
        assert service.inspect()["actions"] == ["initialize", "grants"]
        assert service.apply()["exit_code"] == 0
        assert build_plan(snapshot(cfg, admin, reader)) == []
    finally:
        service.close()


@pytest.mark.parametrize("first", ["tui", "headless"])
def test_native_and_headless_share_real_plan_and_repeat_safely(
    cluster, tmp_path, monkeypatch, first
):
    import asyncio
    import json

    from click.testing import CliRunner
    from textual.widgets import Checkbox, Input

    from tushare_downloader.cli import main
    from tushare_downloader.setup_tui import SetupApp

    cfg, admin, reader, _ = cluster
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith(("PG", "SETUP_")) or key == "LOG_DIR":
            monkeypatch.delenv(key, raising=False)
    values = {
        "PGHOST": cfg.pg_host,
        "PGPORT": str(cfg.pg_port),
        "PGDATABASE": cfg.pg_database,
        "PGUSER": cfg.pg_user,
        "SETUP_READER_USER": reader,
        "LOG_DIR": str(tmp_path / "logs"),
    }
    config = tmp_path / ".env"
    config.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    original = config.read_bytes()
    credentials = tmp_path / "credentials.json"
    credentials.write_text(
        json.dumps(
            {
                "version": 1,
                "admin": {"user": admin.pg_user},
                "writer": {"allow_passwordless_creation": True},
                "reader": {"allow_passwordless_creation": True},
            }
        )
    )
    credentials.chmod(0o600)
    args = ["setup", "--headless", "--credentials-file", str(credentials)]
    check = CliRunner().invoke(main, args)
    assert check.exit_code == 4, check.output
    logs = list((tmp_path / "logs/setup").glob("*.jsonl"))
    events = [json.loads(line) for line in logs[0].read_text().splitlines()]
    headless_plan = next(event["actions"] for event in events if event["event"] == "plan_created")

    async def native(execute):
        app = SetupApp(config_path=config, values=values)
        try:
            async with app.run_test(size=(120, 30)) as pilot:
                app.query_one("#admin_user", Input).value = admin.pg_user
                await pilot.pause()
                await app.check_connection()
                plan = list(app.inspection["actions"])
                if execute:
                    for role in ("writer", "reader"):
                        app.query_one("#" + role + "_passwordless", Checkbox).value = True
                    await pilot.pause()
                    await app.check_connection()
                    assert app.can_apply
                    app.confirm_target(cfg.pg_database)
                    await pilot.pause()
                    app.screen.query_one("#confirmation", Input).value = cfg.pg_database
                    await pilot.pause()
                    app.screen.confirm()
                    await pilot.pause()  # Dispatch the modal's deferred dismissal callback.
                    await app.workers.wait_for_complete()
                    assert app.final_result["exit_code"] == 0, app.final_result
                    assert app.final_result["completed"] == plan
                else:
                    assert not app.applied
                return plan
        finally:
            if app.session:
                app.session.close()

    assert asyncio.run(native(False)) == headless_plan
    assert headless_plan == [
        "create-writer",
        "create-reader",
        "create-database",
        "initialize",
        "grants",
    ]
    if first == "tui":
        assert asyncio.run(native(True)) == headless_plan
    else:
        result = CliRunner().invoke(main, args + ["--apply"])
        assert result.exit_code == 0, result.output
    before_repeat = snapshot(cfg, admin, reader)
    assert build_plan(before_repeat) == []
    result = CliRunner().invoke(main, args + ["--apply"])
    assert result.exit_code == 0, result.output
    assert "Applying:" not in result.output
    assert asyncio.run(native(False)) == []
    assert snapshot(cfg, admin, reader) == before_repeat
    assert config.read_bytes() == original


def test_managed_database_without_reader_only_plans_reader_setup(cluster, tmp_path):
    from tushare_downloader.setup_service import SetupSession

    cfg, admin, reader, conn = cluster
    facts = snapshot(cfg, admin, reader)
    # Build a managed writer-owned database while intentionally omitting the reader.
    for action in ("create-writer", "create-database", "initialize"):
        facts = apply_step(facts, action, cfg, admin, reader)
    original_id = facts["database_id"]
    assert facts["kind"] == "managed"
    assert not facts["reader_exists"]
    assert facts["missing"] == []
    readonly = SetupSession(
        replace(cfg, log_dir=tmp_path), reader, {"reader": {"allow_passwordless_creation": True}}
    )
    try:
        checked = readonly.inspect()
        assert checked["readiness"] == "needs_configuration"
        assert checked["actions"] == ["create-reader", "grants"]
        refused = readonly.apply()
        assert refused["exit_code"] == 4
        assert refused["reason_code"] == "privileges_required"
        assert refused["completed"] == []
        assert not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (reader,)).fetchone()
        assert snapshot(cfg, admin, reader) == facts
    finally:
        readonly.close()
    authorized = SetupSession(
        replace(cfg, log_dir=tmp_path),
        reader,
        {"admin": {"user": admin.pg_user}, "reader": {"allow_passwordless_creation": True}},
    )
    try:
        assert authorized.inspect()["actions"] == ["create-reader", "grants"]
        result = authorized.apply()
        assert result["exit_code"] == 0
        assert result["completed"] == ["create-reader", "grants"]
        assert result["writer_verification"] == "verified"
        assert result["reader_verification"] == "verified"
        state = snapshot(cfg, admin, reader)
        assert state["database_id"] == original_id
        assert build_plan(state) == []
    finally:
        authorized.close()


def test_documented_backup_restore_preserves_data_identity_and_reader_access(cluster):
    import subprocess
    from datetime import UTC, date, datetime
    from decimal import Decimal
    from pathlib import Path

    from tushare_downloader.apis import get_api
    from tushare_downloader.planning import Block
    from tushare_downloader.storage import StorageError, Store

    cfg, admin, reader, administrator = cluster
    psql = os.environ.get("SETUP_TEST_PSQL")
    if not psql:
        pytest.fail("Set SETUP_TEST_PSQL to locate compatible PostgreSQL backup tools.")
    binary_dir = Path(psql).parent
    suffix = ".exe" if psql.endswith(".exe") else ""
    dump_tool, restore_tool = [binary_dir / (name + suffix) for name in ("pg_dump", "pg_restore")]
    assert dump_tool.is_file() and restore_tool.is_file()
    facts = snapshot(cfg, admin, reader)
    for action in build_plan(facts):
        facts = apply_step(facts, action, cfg, admin, reader)
    api = get_api("daily_basic")
    day = date(2024, 1, 2)
    stamp = datetime(2024, 1, 3, tzinfo=UTC)
    block = Block(1, day, day, day, day)

    def connect_to(name, user):
        return psycopg.connect(
            host=cfg.pg_host, port=cfg.pg_port, dbname=name, user=user, autocommit=True
        )

    def data(conn):
        tables = conn.execute(
            "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('raw','meta') ORDER BY 1,2"
        ).fetchall()
        return {
            f"{schema}.{table}": conn.execute(
                sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text").format(
                    sql.Identifier(schema, table)
                )
            ).fetchall()
            for schema, table in tables
        }

    with connect_to(cfg.pg_database, cfg.pg_user) as source:
        store = Store(source)
        rows = [
            (key, day, *[Decimal("1.25") for _ in api.fields[2:]])
            for key in ("000001.SZ", "000002.SZ")
        ]
        store.merge(api, block, rows, stamp)
        source.execute("UPDATE raw.daily_basic SET _is_stale=true WHERE ts_code='000002.SZ'")
        before = data(source)
        identity = store.identity()[0]
    common = ["-h", cfg.pg_host, "-p", str(cfg.pg_port), "-U", cfg.pg_user, "--no-password"]
    archive = subprocess.run(
        [str(dump_tool), *common, "-d", cfg.pg_database, "--format=custom"],
        capture_output=True,
        check=True,
    ).stdout
    assert archive.startswith(b"PGDMP")
    restored_name = cfg.pg_database + "_restore"
    administrator.execute(
        sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(restored_name), sql.Identifier(cfg.pg_user)
        )
    )
    try:
        subprocess.run(
            [
                str(restore_tool),
                *common,
                "--dbname",
                restored_name,
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                "--single-transaction",
            ],
            input=archive,
            capture_output=True,
            check=True,
        )
        with connect_to(restored_name, cfg.pg_user) as restored:
            store = Store(restored)
            assert data(restored) == before
            assert store.initialize() == identity
            assert data(restored) == before
            assert store.counts(api) == (1, 1)
            with pytest.raises(StorageError):
                store.clean(api, apply=True, database=cfg.pg_database, database_id=identity)
            assert data(restored) == before
        selected = replace(cfg, pg_database=restored_name)
        facts = snapshot(selected, admin, reader)
        actions = build_plan(facts)
        assert actions == ["grants"]
        apply_step(facts, "grants", selected, admin, reader)
        with connect_to(restored_name, reader) as readonly:
            assert readonly.execute("SELECT count(*) FROM raw.daily_basic").fetchone()[0] == 2
            for statement in (
                "UPDATE raw.daily_basic SET close=0",
                "DELETE FROM raw.daily_basic",
                "TRUNCATE raw.daily_basic",
            ):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    readonly.execute(statement)
    finally:
        owner = administrator.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (restored_name,)
        ).fetchone()
        assert owner == (cfg.pg_user,), "Unexpected restore database owner; refusing cleanup"
        administrator.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(restored_name)))
