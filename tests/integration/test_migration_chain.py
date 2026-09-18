"""MG03/04: real transactions across a synthetic three-step version chain."""

import psycopg
import pytest
from psycopg.types.json import Jsonb

from tushare_downloader.migration_chain import Migration, execute_steps, plan
from tushare_downloader.storage import CommitUnknown, StorageError


@pytest.mark.parametrize("lost_commit", [False, True])
def test_second_step_failure_keeps_only_confirmed_commits(db, lost_commit):
    db.initialize()
    identity, versions = db.identity()
    versions["fixture"] = "1"
    db.conn.execute("UPDATE meta.schema_info SET specs=%s", (Jsonb(versions),))
    db.conn.execute("CREATE TABLE raw.fixture(value integer)")
    steps = tuple(Migration(f"fixture-{n}", "fixture", str(n), str(n + 1)) for n in range(1, 4))

    def handler(store, step):
        if step.source != "3":
            store.conn.execute("INSERT INTO raw.fixture VALUES (%s)", (int(step.source),))
        if step.source == "2" and not lost_commit:
            raise StorageError("Injected second-step failure")

    class LoseSecondCommit:
        count = 0

        def __getattr__(self, name):
            return getattr(db.conn, name)

        def execute(self, statement, params=None):
            result = db.conn.execute(statement, params)
            if statement == "COMMIT":
                self.count += 1
                if self.count == 2:
                    raise psycopg.OperationalError("Injected acknowledgement loss")
            return result

    connection = LoseSecondCommit() if lost_commit else db.conn
    events = []
    with pytest.raises(CommitUnknown if lost_commit else StorageError):
        execute_steps(
            connection,
            steps,
            str(identity),
            versions,
            {s.id: handler for s in steps},
            lambda *args: events.append(args),
        )
    actual = db.identity()[1]
    assert actual["fixture"] == ("3" if lost_commit else "2")
    assert db.conn.execute("SELECT value FROM raw.fixture ORDER BY value").fetchall() == (
        [(1,), (2,)] if lost_commit else [(1,)]
    )
    assert [f["action"] for e, f in events if e == "step_finished"] == ["fixture-1"]

    def finish(store, step):
        if step.source == "2":
            store.conn.execute("INSERT INTO raw.fixture VALUES (2)")

    pending = plan(actual, {"fixture": "4"}, steps)
    execute_steps(
        db.conn, pending, str(identity), actual, {s.id: finish for s in steps}, lambda *args: None
    )
    assert db.identity()[1]["fixture"] == "4"
    assert db.conn.execute("SELECT value FROM raw.fixture ORDER BY value").fetchall() == [
        (1,),
        (2,),
    ]


def test_writer_lock_held_across_commits(db):
    from tushare_downloader.storage import LOCK_KEY

    db.initialize()
    identity, versions = db.identity()
    versions["fixture"] = "1"
    db.conn.execute("UPDATE meta.schema_info SET specs=%s", (Jsonb(versions),))
    steps = (Migration("a", "fixture", "1", "2"), Migration("b", "fixture", "2", "3"))
    with psycopg.connect(db.test_dsn, autocommit=True) as other:

        def observe(event, fields):
            assert other.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone() == (
                False,
            )

        execute_steps(
            db.conn,
            steps,
            str(identity),
            versions,
            {s.id: lambda *args: None for s in steps},
            observe,
        )
        assert other.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone() == (True,)
