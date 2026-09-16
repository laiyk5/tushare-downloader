"""Real loopback connection failures with bounded setup workers; no PostgreSQL required."""

import multiprocessing
import socket
import time
from datetime import timedelta

import pytest

from tushare_downloader.config import Settings
from tushare_downloader.setup_service import DatabaseBackend, SetupSession


@pytest.mark.parametrize("accept_connections", [False, True], ids=["refused", "unresponsive"])
def test_failed_connection_is_unknown_within_shared_budget(tmp_path, accept_connections):
    class NoWrites(DatabaseBackend):
        def apply(self, *args):
            raise AssertionError("Unknown connection must never execute changes")

    prior_children = {child.pid for child in multiprocessing.active_children()}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as endpoint:
        endpoint.bind(("127.0.0.1", 0))
        if accept_connections:
            endpoint.listen()  # TCP connects, but no PostgreSQL response ever arrives.
        settings = Settings(
            pg_host="127.0.0.1",
            pg_port=endpoint.getsockname()[1],
            pg_database="isolated_fixture",
            pg_user="fixture_writer",
            log_dir=tmp_path,
            connect_timeout=1,
            inspect_timeout=timedelta(seconds=1),
        )
        session = SetupSession(settings, "fixture_reader", {}, backend=NoWrites())
        try:
            started = time.monotonic()
            checked = session.inspect()
            elapsed = time.monotonic() - started
            assert elapsed <= 4, elapsed  # 1s connect + 1s inspection + 2s scheduling allowance.
            assert checked["readiness"] == "unknown"
            assert checked["facts"] is None
            assert checked["actions"] == []
            assert session.apply()["exit_code"] == 1
            assert {child.pid for child in multiprocessing.active_children()} <= prior_children
        finally:
            session.close()
