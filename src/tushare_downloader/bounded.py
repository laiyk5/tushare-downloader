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


class OperationCancelled(RuntimeError):
    pass


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


def bounded(function, *args, seconds, cancel=None):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_call, args=(sender, function, args), daemon=True)
    deadline = monotonic() + seconds
    process.start()
    sender.close()
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise OperationCancelled("Cancelled; the server outcome may be unknown.")
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise DeadlineExceeded(
                    "Client deadline exceeded; operation outcome may be unknown."
                )
            if receiver.poll(min(0.05, remaining)):
                break
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


def bounded_events(function, *args, seconds, observer, cancel=None):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=True)
    process = context.Process(target=_event_call, args=(sender, function, args), daemon=True)
    deadline = monotonic() + seconds
    first_step = True
    process.start()
    sender.close()
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise OperationCancelled("Cancelled; the server outcome may be unknown.")
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise DeadlineExceeded(
                    "Client deadline exceeded; operation outcome may be unknown."
                )
            if not receiver.poll(min(0.05, remaining)):
                continue
            try:
                reply = receiver.recv()
            except EOFError:
                raise RemoteFailure("Database worker ended without a result.") from None
            if reply[0] == "done":
                return reply[1]
            if reply[0] == "error":
                raise RemoteFailure(*reply[1:])
            _, event, fields = reply
            if event == "step_started":
                if not first_step:
                    deadline = monotonic() + seconds
                first_step = False
            observer(event, fields)
            receiver.send(True)
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)


def _event_call(pipe, function, args):
    def emit(event, fields):
        pipe.send(("event", event, fields))
        if pipe.recv() is not True:
            raise RuntimeError("Parent did not acknowledge migration result.")

    try:
        pipe.send(("done", function(emit, *args)))
    except Exception as error:
        pipe.send(
            ("error", safe_error(error), type(error).__name__, getattr(error, "sqlstate", None))
        )
    finally:
        pipe.close()
