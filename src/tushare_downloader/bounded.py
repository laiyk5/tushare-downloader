"""Short-lived isolated calls with a client deadline (including DNS and lost connections)."""

import multiprocessing
from time import monotonic


class DeadlineExceeded(Exception):
    pass


def _call(pipe, function, args):
    try:
        pipe.send((True, function(*args)))
    except Exception as error:
        # Never send arbitrary driver exceptions, SQL, or connection strings to the caller.
        from .storage import StorageError

        message = str(error) if isinstance(error, StorageError) else type(error).__name__
        pipe.send((False, message))
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
            success, value = receiver.recv()
        except EOFError:
            raise RuntimeError("Database worker ended without a result.") from None
        if not success:
            raise RuntimeError(value)
        return value
    finally:
        receiver.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)
