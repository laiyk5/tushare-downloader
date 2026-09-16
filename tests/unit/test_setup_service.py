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
