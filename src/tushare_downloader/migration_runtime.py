"""Bounded setup adapters for the registered migration chain."""

from time import monotonic

from .apis import APIS
from .bounded import DeadlineExceeded
from .migration import change_suspension, preflight
from .migration_chain import REGISTRY, execute_steps, plan
from .storage import StorageError, Store, connect


class DeadlineConnection:
    def __init__(self, conn, deadline):
        self.conn, self.deadline = conn, deadline

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def execute(self, statement, params=None):
        if (
            statement in {"ROLLBACK", "SET TRANSACTION READ ONLY"}
            if isinstance(statement, str)
            else False
        ):
            return self.conn.execute(statement, params)
        remaining = self.deadline - monotonic()
        if remaining <= 0:
            raise DeadlineExceeded("Migration step deadline exceeded.")
        self.conn.execute(
            "SELECT set_config('statement_timeout',%s,false),set_config('lock_timeout',%s,false)",
            (
                str(max(1, int(min(60, remaining) * 1000))),
                str(max(1, int(min(5, remaining) * 1000))),
            ),
        )
        return self.conn.execute(statement, params)


def selected(specs):
    return plan(specs, {key: api.spec_version for key, api in APIS.items()}, REGISTRY)


def preview_step(settings, expected):
    deadline = monotonic() + settings.setup_step_timeout.total_seconds()
    with connect(settings) as raw:
        conn = DeadlineConnection(raw, deadline)
        store = Store(conn)
        with store.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            identity, specs = store.identity()
            if str(identity) != expected["database_id"] or specs != expected["specs"]:
                raise StorageError("Database changed since inspection.")
            preflight(store)
    return None


def migrate(emit, settings, expected):
    seconds = settings.setup_step_timeout.total_seconds()
    deadline = monotonic() + seconds
    with connect(settings) as raw:
        conn = DeadlineConnection(raw, deadline)
        first = True

        def progress(event, fields):
            nonlocal first
            if event == "step_started":
                if not first:
                    conn.deadline = monotonic() + seconds
                first = False
            emit(event, fields)

        result = execute_steps(
            conn,
            selected(expected["specs"]),
            expected["database_id"],
            expected["specs"],
            {"suspend_d-spec-1-to-2": change_suspension},
            progress,
        )
        return result
