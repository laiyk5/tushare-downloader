"""DBW03/05 and H04-H06: shared orchestration, independent of a terminal."""

from copy import deepcopy

from tushare_downloader.config import Settings
from tushare_downloader.setup_service import SetupSession


class Backend:
    def __init__(self, state):
        self.state = state
        self.writes = []
        self.failure = None

    def inspect(self, *args):
        return deepcopy(self.state)

    def apply(self, expected, action, *args):
        self.writes.append(action)
        if action == self.failure:
            raise RuntimeError("connection lost")
        if action == "create-reader":
            self.state["reader_exists"] = True
        if action == "grants":
            self.state["grants_needed"] = False
        if action == "initialize":
            self.state["missing"] = []
        return deepcopy(self.state)

    def verify(self, *args):
        return {"writer": "verified", "reader": "verified"}


def facts(**changes):
    state = dict(
        kind="managed",
        roles_safe=True,
        writer_exists=True,
        reader_exists=True,
        grants_needed=False,
        missing=[],
        database_id="fixture",
    )
    return state | changes


def session(tmp_path, backend, credentials=None):
    return SetupSession(Settings(log_dir=tmp_path), "research", credentials or {}, backend=backend)


def test_ready_and_repeated_apply_do_not_mutate(tmp_path):
    backend = Backend(facts())
    app = session(tmp_path, backend)
    assert app.inspect()["readiness"] == "ready"
    assert app.apply()["exit_code"] == 0
    assert backend.writes == []


def test_missing_creation_credentials_fail_before_all_writes(tmp_path):
    backend = Backend(facts(reader_exists=False, grants_needed=True))
    app = session(tmp_path, backend)
    assert app.inspect()["readiness"] == "needs_configuration"
    result = app.apply()
    assert result["exit_code"] == 4
    assert backend.writes == []


def test_changed_plan_is_never_silently_expanded(tmp_path):
    backend = Backend(facts(grants_needed=True))
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()
    backend.state["reader_exists"] = False
    assert app.apply()["exit_code"] == 1
    assert backend.writes == []


def test_failure_retains_completed_and_does_not_retry(tmp_path):
    backend = Backend(facts(reader_exists=False, grants_needed=True))
    backend.failure = "grants"
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()
    result = app.apply()
    assert result["exit_code"] == 1
    assert result["completed"] == ["create-reader"]
    assert result["unknown"] == ["grants"]
    assert backend.writes == ["create-reader", "grants"]


def test_unknown_is_not_missing(tmp_path):
    backend = Backend(facts())

    def unavailable(*args):
        raise RuntimeError("authentication unavailable")

    backend.inspect = unavailable
    app = session(tmp_path, backend)
    assert app.inspect()["readiness"] == "unknown"
    assert app.apply()["exit_code"] == 1
    assert backend.writes == []


def test_unsupported_is_not_a_repair_plan(tmp_path):
    backend = Backend(facts(kind="external"))
    app = session(tmp_path, backend)
    assert app.inspect()["readiness"] == "unsupported"
    assert app.apply()["exit_code"] == 5
    assert backend.writes == []


def test_cancel_before_execution_preserves_every_pending_step(tmp_path):
    backend = Backend(facts(reader_exists=False, grants_needed=True))
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()
    app.cancelled = True
    result = app.apply()
    assert result["exit_code"] == 130
    assert backend.writes == []
    assert result["not_attempted"] == ["create-reader", "grants"]


def test_known_database_rejection_is_failed_not_unknown(tmp_path):
    from tushare_downloader.bounded import RemoteFailure

    backend = Backend(facts(grants_needed=True))

    def denied(*args):
        raise RemoteFailure("Permission denied.", "InsufficientPrivilege", "42501")

    backend.apply = denied
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()
    result = app.apply()
    assert result["exit_code"] == 1
    assert result["failed"] == ["grants"]
    assert result["unknown"] == []


def test_writer_lock_keeps_exit_code_three(tmp_path):
    from tushare_downloader.bounded import RemoteFailure

    backend = Backend(facts(missing=["daily"]))

    def locked(*args):
        raise RemoteFailure("Writer lock is held.", "BusyError", None)

    backend.apply = locked
    app = session(tmp_path, backend)
    app.inspect()
    result = app.apply()
    assert result["exit_code"] == 3
    assert result["failed"] == ["initialize"]


def test_missing_execution_privilege_blocks_entire_plan(tmp_path):
    backend = Backend(facts(reader_exists=False, grants_needed=True))
    backend.preflight = lambda *args: "privileges_required"
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()
    assert app.apply()["exit_code"] == 4
    assert backend.writes == []


def test_cancel_during_mutation_reports_unknown_and_no_next_step(tmp_path):
    from tushare_downloader.bounded import OperationCancelled

    backend = Backend(facts(reader_exists=False, grants_needed=True))

    def cancelled(*args):
        raise OperationCancelled("Cancelled")

    backend.apply = cancelled
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()
    result = app.apply()
    assert result["exit_code"] == 130
    assert result["unknown"] == ["create-reader"]
    assert result["not_attempted"] == ["grants"]


def test_tui_rechecks_share_log_and_do_not_finish_session_early(tmp_path):
    import json

    from tushare_downloader.setup_events import SetupLog

    log = SetupLog(tmp_path, "tui", {})
    first = SetupSession(
        Settings(log_dir=tmp_path),
        "research",
        {},
        mode="tui",
        backend=Backend(facts()),
        event_log=log,
    )
    first.inspect()
    first.apply()
    first.close()
    second = SetupSession(
        Settings(log_dir=tmp_path),
        "research",
        {},
        mode="tui",
        backend=Backend(facts()),
        event_log=log,
    )
    second.inspect()
    second.close()
    rows = [json.loads(line) for line in log.path.read_text().splitlines()]
    assert [row["plan_seq"] for row in rows if row["event"] == "plan_created"] == [1, 2]
    assert not any(row["event"] == "session_finished" for row in rows)
    log.emit("session_finished", exit_code=0)
    log.close()


def test_authentication_recovery_only_verifies_and_keeps_completed_steps(tmp_path):
    backend = Backend(facts(reader_exists=False, grants_needed=True))

    def auth_failure(*args):
        raise RuntimeError("authentication failed")

    backend.verify = auth_failure
    app = session(tmp_path, backend, {"reader": {"password": "wrong"}})
    app.inspect()
    failed = app.apply()
    assert failed["exit_code"] == 1
    assert failed["reason_code"] == "verification_failed"
    assert failed["completed"] == ["create-reader", "grants"]
    writes = list(backend.writes)

    def corrected(settings, reader_settings):
        assert reader_settings.pg_password == "corrected"
        return {"writer": "verified", "reader": "verified"}

    backend.verify = corrected
    recovered = app.retry_verification(reader_password="corrected")
    assert recovered["exit_code"] == 0
    assert recovered["completed"] == failed["completed"]
    assert backend.writes == writes


def test_authentication_recovery_refuses_replaced_database(tmp_path):
    backend = Backend(facts(grants_needed=True))

    def failed(*args):
        raise RuntimeError("authentication failed")

    backend.verify = failed
    app = session(tmp_path, backend, {"reader": {"password": "wrong"}})
    app.inspect()
    app.apply()
    backend.state["database_id"] = "replacement"
    backend.verify = lambda *args: {"writer": "verified", "reader": "verified"}
    result = app.retry_verification(reader_password="corrected")
    assert result["exit_code"] == 1
    assert result["reason_code"] == "plan_changed"
    assert backend.writes == ["grants"]


def test_reader_rejection_preserves_verified_writer_without_exposing_error(monkeypatch):
    from dataclasses import replace

    import psycopg

    from tushare_downloader import setup_service

    settings = Settings()
    reader = replace(settings, pg_user="research")
    calls = []

    def login(config):
        calls.append(config.pg_user)
        if config.pg_user == "research":
            raise psycopg.OperationalError("password authentication failed secret=private")
        return "verified"

    monkeypatch.setattr(setup_service, "_login", login)
    result = setup_service._verify(settings, reader)
    assert result == {"writer": "verified", "reader": "failed"}
    assert calls == [settings.pg_user, "research"]


def test_writer_rejection_does_not_claim_reader_was_checked(monkeypatch):
    from dataclasses import replace

    import psycopg

    from tushare_downloader import setup_service

    calls = []

    def login(config):
        calls.append(config.pg_user)
        raise psycopg.OperationalError("password authentication failed secret=private")

    monkeypatch.setattr(setup_service, "_login", login)
    settings = Settings()
    result = setup_service._verify(settings, replace(settings, pg_user="research"))
    assert result == {"writer": "failed", "reader": "not_checked"}
    assert calls == [settings.pg_user]


def test_partial_account_verification_is_failure_with_completed_operations(tmp_path):
    import json

    backend = Backend(facts(grants_needed=True))
    backend.verify = lambda *args: {"writer": "verified", "reader": "failed"}
    app = session(tmp_path, backend, {"reader": {"password": "private"}})
    app.inspect()
    result = app.apply()
    assert result["exit_code"] == 1
    assert result["completed"] == ["grants"]
    assert result["writer_verification"] == "verified"
    assert result["reader_verification"] == "failed"
    assert app.verification_pending
    rows = [json.loads(line) for line in app.log.path.read_text().splitlines()]
    event = next(row for row in rows if row["event"] == "verification_finished")
    assert event["outcome"] == "failed"
    assert event["writer_verification"] == "verified"
    assert event["reader_verification"] == "failed"
    backend.verify = lambda *args: {"writer": "verified", "reader": "verified"}
    assert app.retry_verification(reader_password="corrected")["exit_code"] == 0
    assert backend.writes == ["grants"]
    app.close()


def test_cancellation_during_prewrite_recheck_is_interrupt_not_runtime_failure(tmp_path):
    from tushare_downloader.bounded import OperationCancelled

    backend = Backend(facts(grants_needed=True))
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    app.inspect()

    def interrupted(*args):
        raise OperationCancelled("Cancelled")

    backend.inspect = interrupted
    result = app.apply()
    assert result["exit_code"] == 130
    assert result["reason_code"] == "interrupted"
    assert result["not_attempted"] == ["grants"]
    assert result["unknown"] == []
    assert backend.writes == []
    app.close()


def test_final_event_failure_is_reported_as_log_failure(tmp_path, monkeypatch):
    from tushare_downloader.setup_events import SetupLog

    backend = Backend(facts())
    app = session(tmp_path, backend)
    app.inspect()
    emit = SetupLog.emit

    def fail(self, event, **kwargs):
        if event == "session_finished":
            raise OSError("private error")
        return emit(self, event, **kwargs)

    monkeypatch.setattr(SetupLog, "emit", fail)
    result = app.apply()
    assert result["exit_code"] == 1
    assert result["reason_code"] == "log_failed"
    assert result["readiness"] == "ready"
    assert backend.writes == []
    app.close()


def test_unsupported_and_unknown_checks_keep_safe_reason_codes(tmp_path):
    cases = [
        (facts(kind="external"), "unmanaged_objects"),
        (facts(kind="foreign-empty"), "ownership_conflict"),
        (facts(kind="incompatible"), "incompatible_schema"),
        (facts(roles_safe=False), "role_privilege_conflict"),
    ]
    for state, reason in cases:
        app = session(tmp_path, Backend(state))
        checked = app.inspect()
        assert checked["reason_code"] == reason
        assert app.apply()["reason_code"] == reason
        app.close()


def test_temporary_credentials_preserve_target_and_do_not_cross_accounts(tmp_path):
    from dataclasses import replace

    baseline = Settings(
        pg_host="selected",
        pg_port=5555,
        pg_database="target",
        pg_user="writer",
        pg_password="WRITER_OLD_SECRET",
        pg_sslmode="require",
        log_dir=tmp_path,
    )
    backend = Backend(facts(grants_needed=True))
    seen = []

    def verify(writer, reader):
        seen.append((writer, reader))
        return {"writer": "verified", "reader": "verified"}

    backend.verify = verify
    app = SetupSession(
        baseline,
        "reader",
        {
            "writer": {"password": "WRITER_TEMP_SECRET"},
            "admin": {"user": "administrator", "maintenance_database": "maintenance"},
        },
        backend=backend,
    )
    try:
        assert app.settings == replace(baseline, pg_password="WRITER_TEMP_SECRET")
        assert app.administrator == replace(
            baseline, pg_user="administrator", pg_database="maintenance", pg_password=""
        )
        app.inspect()
        assert app.apply()["exit_code"] == 0
        assert seen[0][1] == replace(baseline, pg_user="reader", pg_password="")
        assert baseline.pg_password == "WRITER_OLD_SECRET"
        assert "SECRET" not in app.log.path.read_text()
    finally:
        app.close()


def test_worker_drops_implicit_identity_and_host_address_overrides(monkeypatch):
    import os

    from tushare_downloader.setup_service import _isolated

    keys = (
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGPASSWORD",
        "PGUSER",
        "PGDATABASE",
        "PGHOST",
        "PGHOSTADDR",
        "PGPORT",
        "PGSSLMODE",
    )
    for key in keys:
        monkeypatch.setenv(key, "UNSELECTED_SECRET")

    def inspect_environment():
        return {key: os.environ.get(key) for key in keys}

    assert _isolated(inspect_environment, ()) == dict.fromkeys(keys)


def test_plan_log_records_safe_before_and_expected_after(tmp_path):
    import json

    backend = Backend(
        facts(reader_exists=False, grants_needed=True, missing=["daily"], private_detail="SECRET")
    )
    app = session(tmp_path, backend, {"reader": {"password": "SECRET"}})
    try:
        app.inspect()
        text = app.log.path.read_text()
        events = [json.loads(line) for line in text.splitlines()]
        plan = next(event for event in events if event["event"] == "plan_created")
        assert plan["before"]["reader_exists"] is False
        assert plan["before"]["missing"] == ["daily"]
        assert plan["after"]["reader_exists"] is True
        assert plan["after"]["missing"] == []
        assert plan["after"]["grants_needed"] is False
        assert "SECRET" not in text
    finally:
        app.close()


def test_grants_by_writer_are_not_logged_as_administrator(tmp_path):
    import json

    app = session(tmp_path, Backend(facts(grants_needed=True)))
    try:
        app.inspect()
        assert app.apply()["exit_code"] == 0
        events = [json.loads(line) for line in app.log.path.read_text().splitlines()]
        event = next(event for event in events if event["event"] == "step_started")
        assert event["actor_role"] == "writer"
    finally:
        app.close()


def test_reader_worker_failure_preserves_verified_writer_and_shared_budget(tmp_path, monkeypatch):
    import json

    from tushare_downloader import setup_service
    from tushare_downloader.bounded import DeadlineExceeded, OperationCancelled

    for error, code in [
        (DeadlineExceeded("SECRET timeout"), 1),
        (OperationCancelled("SECRET cancelled"), 130),
    ]:
        calls = []
        clock = [0.0]

        def now():
            clock[0] += 0.1
            return clock[0]

        def isolated_call(function, verify_function, args, *, seconds, cancel):
            calls.append((args[0].pg_user, seconds))
            if len(calls) == 1:
                return {"writer": "verified", "reader": "not_checked"}
            raise error

        monkeypatch.setattr(setup_service, "bounded", isolated_call)
        monkeypatch.setattr(setup_service, "monotonic", now)
        backend = Backend(facts(grants_needed=True))
        backend.verify = setup_service.DatabaseBackend().verify
        app = session(tmp_path, backend)
        try:
            app.inspect()
            result = app.apply()
            assert result["exit_code"] == code
            assert result["writer_verification"] == "verified"
            assert result["reader_verification"] == "failed"
            assert result["completed"] == ["grants"]
            assert backend.writes == ["grants"]
            assert len(calls) == 2
            assert calls[1][0] == "research"
            assert 0 < calls[1][1] < calls[0][1]
            text = app.log.path.read_text()
            assert "SECRET" not in text
            final = json.loads(text.splitlines()[-1])
            assert final["writer_verification"] == "verified"
            assert final["reader_verification"] == "failed"
            assert final["exit_code"] == code
        finally:
            app.close()


def test_verification_event_failure_keeps_successful_account_results(tmp_path, monkeypatch):
    backend = Backend(facts(grants_needed=True))
    app = session(tmp_path, backend)
    original = app.log.emit

    def fail_verification_event(event, **fields):
        if event == "verification_finished":
            raise OSError("SECRET event failure")
        return original(event, **fields)

    try:
        app.inspect()
        monkeypatch.setattr(app.log, "emit", fail_verification_event)
        result = app.apply()
        assert result["exit_code"] == 1
        assert result["reason_code"] == "log_failed"
        assert result["writer_verification"] == "verified"
        assert result["reader_verification"] == "verified"
        assert result["completed"] == ["grants"]
        assert backend.writes == ["grants"]
        assert "SECRET" not in app.log.path.read_text()
    finally:
        app.close()


def test_login_rejects_unexpected_account_or_database(monkeypatch):
    from contextlib import contextmanager

    import pytest

    from tushare_downloader import setup_service

    settings = Settings(pg_user="writer", pg_database="fixture")
    for identity in [("other_account", "fixture"), ("writer", "other_database")]:

        class Connection:
            def execute(self, *args):
                return self

            def fetchone(self):
                return identity

        @contextmanager
        def connect(selected):
            yield Connection()

        monkeypatch.setattr(setup_service, "connect", connect)
        with pytest.raises(RuntimeError, match="Unexpected login identity"):
            setup_service._login(settings)


def test_migration_needed_blocks_all_setup_actions(tmp_path):
    backend = Backend(facts(kind="migration", reader_exists=False, grants_needed=True))
    app = session(tmp_path, backend)
    try:
        assert app.inspect()["readiness"] == "migration_needed"
        assert app.apply()["exit_code"] == 4
        assert backend.writes == []
    finally:
        app.close()


def test_migration_plan_precedes_missing_reader_and_requires_confirmation(tmp_path):
    backend = Backend(
        facts(
            kind="migration",
            specs={"suspend_d": "1"},
            database="tushare",
            reader_exists=False,
            grants_needed=True,
        )
    )
    app = session(tmp_path, backend, {"reader": {"password": "temporary"}})
    checked = app.inspect()
    assert checked["readiness"] == "migration_needed"
    assert checked["actions"] == ["suspend_d-spec-1-to-2", "create-reader", "grants"]
    assert app.apply()["exit_code"] == 4
    assert backend.writes == []


def test_wrong_migration_confirmation_is_input_error_before_write(tmp_path):
    backend = Backend(facts(kind="migration", specs={"suspend_d": "1"}, database="tushare"))
    app = session(tmp_path, backend)
    app.inspect()
    assert app.apply(confirm_database="wrong")["exit_code"] == 2
    assert backend.writes == []


def test_migration_interrupt_keeps_unknown_result(tmp_path):
    from tushare_downloader.bounded import OperationCancelled

    class MigratingBackend(Backend):
        def migrate(self, expected, settings, observer):
            observer(
                "step_started",
                dict(
                    action="suspend_d-spec-1-to-2",
                    step_id=1,
                    migration_id="suspend_d-spec-1-to-2",
                    scope="suspend_d",
                    from_version="1",
                    to_version="2",
                    database_id="fixture",
                ),
            )
            raise OperationCancelled("interrupted")

    app = session(
        tmp_path,
        MigratingBackend(facts(kind="migration", specs={"suspend_d": "1"}, database="tushare")),
    )
    app.inspect()
    result = app.apply(confirm_database="tushare")
    assert result["exit_code"] == 130
    assert result["unknown"] == ["suspend_d-spec-1-to-2"]
    assert result["completed"] == []


def test_migration_commit_record_survives_log_failure(tmp_path):
    class MigratingBackend(Backend):
        def migrate(self, expected, settings, observer):
            fields = dict(
                action="suspend_d-spec-1-to-2",
                step_id=1,
                migration_id="suspend_d-spec-1-to-2",
                scope="suspend_d",
                from_version="1",
                to_version="2",
                database_id="fixture",
            )
            observer("step_started", fields)
            observer("step_finished", fields | {"outcome": "completed"})

    app = session(
        tmp_path,
        MigratingBackend(facts(kind="migration", specs={"suspend_d": "1"}, database="tushare")),
    )
    app.inspect()
    original = app.log.emit

    def fail(event, **fields):
        if event == "step_finished":
            raise OSError("disk full")
        return original(event, **fields)

    app.log.emit = fail
    result = app.apply(confirm_database="tushare")
    assert result["exit_code"] == 1
    assert result["completed"] == ["suspend_d-spec-1-to-2"]
    assert result["unknown"] == []


def test_successful_migration_clears_migration_needed_reason(tmp_path):
    class MigratingBackend(Backend):
        def migrate(self, expected, settings, observer):
            fields = dict(
                action="suspend_d-spec-1-to-2", step_id=1, migration_id="suspend_d-spec-1-to-2"
            )
            observer("step_started", fields)
            self.state.update(kind="managed", specs={"suspend_d": "2"})
            observer("step_finished", fields | {"outcome": "completed"})

    app = session(
        tmp_path,
        MigratingBackend(facts(kind="migration", specs={"suspend_d": "1"}, database="tushare")),
    )
    app.inspect()
    result = app.apply(confirm_database="tushare")
    assert result["exit_code"] == 0
    assert result["readiness"] == "ready"
    assert result["reason_code"] is None
