"""Drop real PostgreSQL COMMIT traffic, not a mocked Store.merge exception."""

import socket
import threading
from contextlib import contextmanager, suppress
from datetime import UTC, date, datetime
from decimal import Decimal

import psycopg
import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.planning import Block
from tushare_downloader.storage import CommitUnknown, Store

pytestmark = pytest.mark.integration
API = get_api("daily_basic")
DAY = date(2024, 1, 2)
BLOCK = Block((DAY - API.block_origin).days, DAY, DAY, DAY, DAY)
STAMP = datetime(2024, 1, 3, tzinfo=UTC)
ROW = ("001.SZ", DAY, *[Decimal("1") for _ in API.fields[2:]])


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise EOFError
        data.extend(part)
    return bytes(data)


@contextmanager
def drop_commit(dsn, when):
    """Forward the wire protocol; disconnect before COMMIT or hide its completed reply."""
    info = psycopg.conninfo.conninfo_to_dict(dsn)
    target = (info.get("host", "localhost"), int(info.get("port", 5432)))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(10)
    sockets = []
    reached = threading.Event()
    commit = threading.Event()
    errors = []

    def close_all():
        for sock in sockets:
            with suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)
            with suppress(OSError):
                sock.close()

    def frontend(client, server):
        try:
            length = read_exact(client, 4)
            server.sendall(length + read_exact(client, int.from_bytes(length, "big") - 4))
            while True:
                kind = read_exact(client, 1)
                length = read_exact(client, 4)
                body = read_exact(client, int.from_bytes(length, "big") - 4)
                if kind == b"Q" and body.rstrip(b"\0").strip().upper() == b"COMMIT":
                    commit.set()
                    if when == "before":
                        reached.set()
                        close_all()
                        return
                server.sendall(kind + length + body)
        except (EOFError, OSError):
            pass
        finally:
            close_all()

    def relay():
        worker = None
        try:
            client, _ = listener.accept()
            server = socket.create_connection(target, timeout=5)
            client.settimeout(10)
            server.settimeout(10)
            sockets.extend((client, server))
            worker = threading.Thread(target=frontend, args=(client, server), daemon=True)
            worker.start()
            while True:
                kind = read_exact(server, 1)
                length = read_exact(server, 4)
                body = read_exact(server, int.from_bytes(length, "big") - 4)
                if commit.is_set() and when == "after":
                    if kind == b"Z":
                        reached.set()
                        close_all()
                        return
                    continue
                client.sendall(kind + length + body)
        except (EOFError, OSError):
            pass
        except Exception as error:
            errors.append(type(error).__name__)
        finally:
            close_all()
            if worker:
                worker.join(timeout=2)

    thread = threading.Thread(target=relay, daemon=True)
    thread.start()
    info.update(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=str(listener.getsockname()[1]),
        sslmode="disable",
        gssencmode="disable",
        connect_timeout="5",
    )
    try:
        yield psycopg.conninfo.make_conninfo(**info), reached
    finally:
        close_all()
        listener.close()
        thread.join(timeout=3)
        assert not thread.is_alive(), "wire proxy failed to stop"
        assert not errors, errors


@pytest.mark.parametrize("when,committed", [("before", False), ("after", True)])
def test_real_commit_confirmation_loss(db, when, committed):
    db.initialize()
    with drop_commit(db.test_dsn, when) as (dsn, reached):
        with psycopg.connect(dsn, autocommit=True) as conn:
            store = Store(conn)
            with pytest.raises(CommitUnknown):
                store.merge(API, BLOCK, [ROW], STAMP)
        assert reached.wait(2)
    assert db.counts(API) == ((1, 0) if committed else (0, 0))
    observation = db.observation(API, BLOCK)
    assert (observation is not None) == committed
    # A fresh invocation inspects the atomic result and can safely re-request.
    assert db.merge(API, BLOCK, [ROW], STAMP).inserted == (0 if committed else 1)
    assert db.counts(API) == (1, 0)


def test_real_backend_termination_rolls_back(db):
    db.initialize()
    with psycopg.connect(db.test_dsn, autocommit=True) as conn:
        store = Store(conn)
        pid = conn.info.backend_pid
        with pytest.raises(psycopg.Error), store.transaction():
            conn.execute("""INSERT INTO raw.daily_basic
                (ts_code,trade_date,_is_stale,_last_seen_at,_updated_at)
                VALUES ('001.SZ','2024-01-02',false,now(),now())""")
            db.conn.execute("SELECT pg_terminate_backend(%s)", (pid,))
            conn.execute("SELECT 1")
    assert db.counts(API) == (0, 0)


def test_ctrl_c_rolls_back_transaction(db):
    db.initialize()
    with pytest.raises(KeyboardInterrupt), db.transaction():
        db.conn.execute("""INSERT INTO raw.daily_basic
            (ts_code,trade_date,_is_stale,_last_seen_at,_updated_at)
            VALUES ('001.SZ','2024-01-02',false,now(),now())""")
        raise KeyboardInterrupt
    assert db.counts(API) == (0, 0)
