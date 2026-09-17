"""MG03: transaction/version expectations, independent of PostgreSQL migration SQL."""

from contextlib import contextmanager
from copy import deepcopy

import pytest

from tushare_downloader import migration_chain as chain
from tushare_downloader.storage import StorageError


class FakeStore:
    def __init__(self, conn):
        self.conn = conn

    def identity(self):
        return "fixture", dict(self.conn.specs)

    @contextmanager
    def writer(self):
        self.conn.locks += 1
        try:
            yield
        finally:
            self.conn.locks -= 1

    @contextmanager
    def transaction(self):
        original = deepcopy((self.conn.specs, self.conn.values))
        try:
            yield
        except BaseException:
            self.conn.specs, self.conn.values = original
            raise


class Connection:
    def __init__(self):
        self.specs = {"event": "1"}
        self.values = []
        self.locks = 0

    def execute(self, sql, params=None):
        if sql.startswith("UPDATE meta.schema_info"):
            self.specs = dict(params[0].obj)


@pytest.fixture
def prepared(monkeypatch):
    monkeypatch.setattr(chain, "Store", FakeStore)
    steps = tuple(chain.Migration(f"event-{i}", "event", str(i), str(i + 1)) for i in range(1, 4))
    return Connection(), steps


def test_chain_keeps_lock_across_steps_and_commits_each_version(prepared):
    conn, steps = prepared
    events = []

    def change(store, step):
        assert conn.locks == 1
        conn.values.append(step.source)

    handlers = {s.id: change for s in steps}
    chain.execute_steps(
        conn, steps, "fixture", {"event": "1"}, handlers, lambda *args: events.append(args)
    )
    assert conn.specs == {"event": "4"}
    assert conn.values == ["1", "2", "3"]
    assert conn.locks == 0
    assert [fields["outcome"] for event, fields in events if event == "step_finished"] == [
        "completed"
    ] * 3


def test_second_failure_preserves_first_and_rerun_starts_at_actual_version(prepared):
    conn, steps = prepared
    calls = []

    def change(store, step):
        calls.append(step.source)
        conn.values.append(step.source)
        if step.source == "2":
            raise StorageError("Injected failure")

    with pytest.raises(StorageError):
        chain.execute_steps(
            conn,
            steps,
            "fixture",
            dict(conn.specs),
            {s.id: change for s in steps},
            lambda *args: None,
        )
    assert conn.specs == {"event": "2"}
    assert conn.values == ["1"]
    assert calls == ["1", "2"]
    remaining = chain.plan(conn.specs, {"event": "4"}, steps)
    chain.execute_steps(
        conn,
        remaining,
        "fixture",
        dict(conn.specs),
        {s.id: lambda store, step: conn.values.append(step.source) for s in steps},
        lambda *args: None,
    )
    assert conn.values == ["1", "2", "3"]
    assert conn.specs == {"event": "4"}


def test_plan_changed_before_write_is_rejected(prepared):
    conn, steps = prepared
    conn.specs["event"] = "2"
    with pytest.raises(StorageError):
        chain.execute_steps(conn, steps, "fixture", {"event": "1"}, {}, lambda *args: None)
    assert conn.values == []


def test_log_failure_after_commit_stops_following_steps(prepared):
    conn, steps = prepared

    def emit(event, fields):
        if event == "step_finished":
            raise OSError("Cannot write log")

    with pytest.raises(OSError):
        chain.execute_steps(
            conn,
            steps,
            "fixture",
            dict(conn.specs),
            {s.id: lambda store, step: None for s in steps},
            emit,
        )
    assert conn.specs == {"event": "2"}
