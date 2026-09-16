"""Shared finite setup orchestration, independent of terminal widgets."""

import os
from dataclasses import replace
from time import monotonic

from .bounded import DeadlineExceeded, RemoteFailure, bounded
from .setup_credentials import writer_password
from .setup_db import apply_step, build_plan, name, snapshot, timeouts
from .setup_events import SetupLog
from .storage import connect


def _login(settings):
    with connect(settings) as conn:
        timeouts(conn, settings.inspect_timeout.total_seconds())
        row = conn.execute("SELECT current_user,current_database()").fetchone()
        if row != (settings.pg_user, settings.pg_database):
            raise RuntimeError("Unexpected login identity.")
    return "verified"


def _inspect(settings, administrator, reader):
    facts = snapshot(settings, administrator, reader)
    if facts["kind"] == "managed" and facts["writer_exists"]:
        _login(settings)
    return facts


def _verify(settings, reader_settings):
    result = {"writer": _login(settings), "reader": "not_checked"}
    if reader_settings is not None:
        result["reader"] = _login(reader_settings)
    return result


def _isolated(function, args):
    # Runs only in the short-lived spawned database worker. Explicit identity
    # cannot inherit a service definition or another account's environment password.
    for key in (
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGPASSWORD",
        "PGUSER",
        "PGDATABASE",
        "PGHOST",
        "PGPORT",
        "PGSSLMODE",
    ):
        os.environ.pop(key, None)
    return function(*args)


def _preflight(settings, administrator, reader, credentials, facts, actions):
    if any(
        action in actions
        for action in ("create-writer", "create-reader", "create-database", "grants")
    ):
        with connect(administrator) as conn:
            timeouts(conn, settings.inspect_timeout.total_seconds())
            superuser, create_role, create_db = conn.execute(
                "SELECT rolsuper,rolcreaterole,rolcreatedb FROM pg_roles WHERE rolname=current_user"
            ).fetchone()
            if any(a in actions for a in ("create-writer", "create-reader")) and not (
                superuser or create_role
            ):
                return "privileges_required"
            if "create-database" in actions:
                if not (superuser or create_db):
                    return "privileges_required"
                if not superuser:
                    if not facts["writer_exists"]:
                        return "privileges_required"
                    if not conn.execute(
                        "SELECT pg_has_role(current_user,%s,'SET')", (settings.pg_user,)
                    ).fetchone()[0]:
                        return "privileges_required"
            if "grants" in actions and not superuser:
                if (
                    not facts["writer_exists"]
                    or not conn.execute(
                        "SELECT pg_has_role(current_user,%s,'USAGE')", (settings.pg_user,)
                    ).fetchone()[0]
                ):
                    return "privileges_required"
    if facts["writer_exists"] and facts["kind"] != "missing":
        _login(settings)
    if "grants" in actions and facts["reader_exists"]:
        connection = replace(
            settings, pg_user=reader, pg_password=credentials.get("reader", {}).get("password", "")
        )
        # Authentication can be checked against an accessible maintenance database
        # when the planned change is precisely a missing CONNECT grant.
        permitted = False
        if facts["kind"] != "missing":
            with connect(administrator) as conn:
                permitted = conn.execute(
                    "SELECT has_database_privilege(%s,%s,'CONNECT')", (reader, settings.pg_database)
                ).fetchone()[0]
        if not permitted:
            connection = replace(
                connection,
                pg_database=credentials.get("admin", {}).get("maintenance_database", "postgres"),
            )
        _login(connection)
    return None


class DatabaseBackend:
    def preflight(self, settings, administrator, reader, credentials, facts, actions):
        return bounded(
            _isolated,
            _preflight,
            (settings, administrator, reader, credentials, facts, actions),
            seconds=settings.connect_timeout + settings.inspect_timeout.total_seconds(),
        )

    def inspect(self, settings, administrator, reader):
        return bounded(
            _isolated,
            _inspect,
            (settings, administrator, reader),
            seconds=settings.connect_timeout + settings.inspect_timeout.total_seconds(),
        )

    def apply(self, expected, action, settings, administrator, reader, password):
        return bounded(
            _isolated,
            apply_step,
            (expected, action, settings, administrator, reader, password),
            seconds=settings.setup_step_timeout.total_seconds(),
        )

    def verify(self, settings, reader_settings):
        return bounded(
            _isolated,
            _verify,
            (settings, reader_settings),
            seconds=settings.connect_timeout + settings.inspect_timeout.total_seconds(),
        )


class SetupSession:
    def __init__(
        self, settings, reader, credentials, *, mode="headless", backend=None, observer=None
    ):
        self.settings = replace(
            settings, pg_password=writer_password(credentials, settings.pg_password)
        )
        self.reader = name(reader)
        name(settings.pg_database)
        name(settings.pg_user)
        if reader == settings.pg_user:
            raise ValueError("Writer and reader must be different roles.")
        self.credentials = credentials
        admin = credentials.get("admin")
        self.administrator = (
            replace(
                self.settings,
                pg_user=admin["user"],
                pg_password=admin.get("password", ""),
                pg_database=admin.get("maintenance_database", "postgres"),
            )
            if admin
            else self.settings
        )
        self.backend = backend or DatabaseBackend()
        self.observer = observer
        self.log = SetupLog(
            settings.log_dir,
            mode,
            dict(
                host=settings.pg_host,
                port=settings.pg_port,
                database=settings.pg_database,
                writer=settings.pg_user,
                reader=reader,
            ),
        )
        self.facts = None
        self.actions = []
        self.readiness = "unknown"
        self.cancelled = False
        self.result = {}
        self._emit("config_loaded")

    def _emit(self, event, **fields):
        self.log.emit(event, **fields)
        if self.observer:
            self.observer(event, fields)

    def inspect(self):
        self.facts = None
        self.actions = []
        started = monotonic()
        try:
            self.facts = self.backend.inspect(self.settings, self.administrator, self.reader)
            try:
                self.actions = build_plan(self.facts)
                self.readiness = "needs_configuration" if self.actions else "ready"
            except ValueError:
                self.readiness = "unsupported"
        except (RuntimeError, DeadlineExceeded):
            self.readiness = "unknown"
        self._emit(
            "inspection_finished",
            outcome=self.readiness,
            duration_ms=round((monotonic() - started) * 1000),
        )
        if self.readiness in {"ready", "needs_configuration"}:
            self.log.plan(self.actions)
        return {"readiness": self.readiness, "actions": list(self.actions), "facts": self.facts}

    def _finish(self, code, completed, failed, unknown, pending, reason=None, verification=None):
        self.result = dict(
            exit_code=code,
            readiness=self.readiness,
            completed=completed,
            failed=failed,
            unknown=unknown,
            not_attempted=pending,
            writer_verification=(verification or {}).get("writer", "not_checked"),
            reader_verification=(verification or {}).get("reader", "not_checked"),
            configuration="not_saved",
        )
        try:
            self._emit(
                "session_finished",
                outcome="completed" if code == 0 else "incomplete",
                reason_code=reason,
                **self.result,
            )
        except OSError:
            self.result["exit_code"] = 1
        return self.result

    def apply(self):
        completed, failed, unknown = [], [], []
        actions = list(self.actions)
        codes = {"unknown": 1, "unsupported": 5}
        if self.readiness in codes:
            return self._finish(codes[self.readiness], [], [], [], actions)
        for action, role, password in (
            ("create-writer", "writer", self.settings.pg_password),
            ("create-reader", "reader", self.credentials.get("reader", {}).get("password")),
        ):
            if (
                action in actions
                and not password
                and not self.credentials.get(role, {}).get("allow_passwordless_creation")
            ):
                return self._finish(4, [], [], [], actions, "credentials_required")
        if actions and hasattr(self.backend, "preflight"):
            try:
                reason = self.backend.preflight(
                    self.settings,
                    self.administrator,
                    self.reader,
                    self.credentials,
                    self.facts,
                    actions,
                )
                if reason:
                    return self._finish(4, [], [], [], actions, reason)
            except (RuntimeError, DeadlineExceeded):
                return self._finish(1, [], [], [], actions, "preflight_failed")
        current = self.facts
        for index, action in enumerate(actions):
            if self.cancelled:
                return self._finish(130, completed, failed, unknown, actions[index:], "interrupted")
            try:
                actual = self.backend.inspect(self.settings, self.administrator, self.reader)
                if actual != current:
                    return self._finish(
                        1, completed, failed, unknown, actions[index:], "plan_changed"
                    )
                self._emit(
                    "step_started",
                    action=action,
                    step_id=index + 1,
                    actor_role="writer" if action == "initialize" else "administrator",
                )
            except (OSError, RuntimeError, DeadlineExceeded):
                return self._finish(
                    1, completed, failed, unknown, actions[index:], "preflight_failed"
                )
            started = monotonic()
            try:
                password = (
                    self.settings.pg_password
                    if action == "create-writer"
                    else self.credentials.get("reader", {}).get("password", "")
                )
                current = self.backend.apply(
                    current, action, self.settings, self.administrator, self.reader, password
                )
                completed.append(action)
            except (RuntimeError, DeadlineExceeded) as error:
                known = isinstance(error, RemoteFailure) and (
                    error.kind in {"BusyError", "StorageError"}
                    or (error.sqlstate or "")[:2]
                    in {"22", "23", "28", "3D", "3F", "40", "42", "53", "55", "0A"}
                )
                if known:
                    failed.append(action)
                    try:
                        self._emit(
                            "step_finished",
                            action=action,
                            step_id=index + 1,
                            outcome="failed",
                            reason_code="database_rejected",
                        )
                    except OSError:
                        return self._finish(
                            1, completed, failed, unknown, actions[index + 1 :], "log_failed"
                        )
                    return self._finish(
                        3 if error.kind == "BusyError" else 1,
                        completed,
                        failed,
                        unknown,
                        actions[index + 1 :],
                        "database_rejected",
                    )
                unknown.append(action)
                try:
                    self._emit(
                        "step_finished",
                        action=action,
                        step_id=index + 1,
                        outcome="unknown",
                        reason_code="execution_unconfirmed",
                    )
                    self.backend.inspect(self.settings, self.administrator, self.reader)
                except (RuntimeError, DeadlineExceeded, OSError):
                    pass
                return self._finish(
                    1, completed, failed, unknown, actions[index + 1 :], "execution_unconfirmed"
                )
            try:
                self._emit(
                    "step_finished",
                    action=action,
                    step_id=index + 1,
                    outcome="completed",
                    duration_ms=round((monotonic() - started) * 1000),
                )
            except OSError:
                return self._finish(
                    1, completed, failed, unknown, actions[index + 1 :], "log_failed"
                )
        verification = {"writer": "verified", "reader": "not_checked"}
        if actions:
            reader_settings = (
                replace(
                    self.settings,
                    pg_user=self.reader,
                    pg_password=self.credentials.get("reader", {}).get("password", ""),
                )
                if any(a in actions for a in ("create-reader", "grants"))
                else None
            )
            try:
                verification = self.backend.verify(self.settings, reader_settings)
                self._emit(
                    "verification_finished",
                    outcome="completed",
                    writer_verification=verification["writer"],
                    reader_verification=verification["reader"],
                )
            except (RuntimeError, DeadlineExceeded, OSError):
                return self._finish(1, completed, failed, unknown, [], "verification_failed")
        self.readiness = "ready"
        self.facts = current
        self.actions = []
        return self._finish(0, completed, failed, unknown, [], verification=verification)

    def finish_check(self, code):
        return self._finish(code, [], [], [], list(self.actions))

    def close(self):
        self.log.close()
