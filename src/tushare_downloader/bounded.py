"""Short-lived isolated calls with a client deadline (including DNS and lost connections)."""

import multiprocessing
import re
from time import monotonic

import psycopg


class RemoteFailure(RuntimeError):
    def __init__(self, message, kind=None, sqlstate=None):
        super().__init__(message)
        self.kind = kind
        self.sqlstate = sqlstate


class DeadlineExceeded(Exception):
    pass


def safe_error(error):
    """Allowlisted diagnostics only: libpq messages can contain connection secrets."""
    from .storage import StorageError

    if isinstance(error, StorageError):
        return str(error)
    if isinstance(error, psycopg.Error):
        message = str(error).lower()
        hints = (
            ("no password supplied", "Authentication failed: no password supplied."),
            ("password authentication failed", "Authentication failed: password was rejected."),
            ("no pg_hba.conf entry", "Server authentication rules do not allow this connection."),
            ("connection refused", "The server refused the connection."),
            ("could not translate host name", "The server host could not be resolved."),
        )
        detail = next((hint for token, hint in hints if token in message), type(error).__name__)
        state = error.sqlstate
        if state and re.fullmatch(r"[0-9A-Z]{5}", state):
            detail += " (SQLSTATE " + state + ")"
        return detail
    return type(error).__name__


def _call(pipe, function, args):
    try:
        pipe.send((True, function(*args)))
    except Exception as error:
        # Never send arbitrary driver exceptions, SQL, or connection strings to the caller.
        pipe.send(
            (False, safe_error(error), type(error).__name__, getattr(error, "sqlstate", None))
        )
    finally:
        pipe.close()


def bounded(function, *args, seconds):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_call, args=(sender, function, args), daemon=True)
    deadline = monotonic() + seconds
    process.start()
    sender.close()
    try:
        if not receiver.poll(max(0, deadline - monotonic())):
            raise DeadlineExceeded("Client deadline exceeded; operation outcome may be unknown.")
        try:
            reply = receiver.recv()
            success, value = reply[:2]
        except EOFError:
            raise RuntimeError("Database worker ended without a result.") from None
        if not success:
            raise RemoteFailure(value, *reply[2:])
        return value
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)
