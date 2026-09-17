"""MG04/07: acknowledgement prevents writes after parent/log failure."""

import time

import pytest

from tushare_downloader.bounded import DeadlineExceeded, bounded_events


def worker(emit, destination):
    emit("step_started", {"action": "first"})
    destination.write_text("first")
    emit("step_finished", {"action": "first", "outcome": "completed"})
    emit("step_started", {"action": "second"})
    destination.write_text("second")
    return "done"


def stuck(emit):
    emit("step_started", {})
    time.sleep(5)


def test_parent_acknowledges_each_step(tmp_path):
    events = []
    target = tmp_path / "writes"
    assert (
        bounded_events(worker, target, seconds=3, observer=lambda e, f: events.append(e)) == "done"
    )
    assert target.read_text() == "second"
    assert events == ["step_started", "step_finished", "step_started"]


def test_log_failure_does_not_allow_next_step(tmp_path):
    target = tmp_path / "writes"

    def observer(event, fields):
        if event == "step_finished":
            raise OSError("log failed")

    with pytest.raises(OSError):
        bounded_events(worker, target, seconds=3, observer=observer)
    assert target.read_text() == "first"


def test_step_client_deadline_terminates_worker():
    with pytest.raises(DeadlineExceeded):
        bounded_events(stuck, seconds=0.5, observer=lambda e, f: None)


def test_cancel_after_worker_starts_ends_without_waiting_for_server():
    from threading import Event

    from tushare_downloader.bounded import OperationCancelled

    cancel = Event()
    observed = []

    def observer(event, fields):
        observed.append(event)
        cancel.set()

    with pytest.raises(OperationCancelled):
        bounded_events(stuck, seconds=3, observer=observer, cancel=cancel)
    assert observed == ["step_started"]
