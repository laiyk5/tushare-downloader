from datetime import date

import pytest
from test_download import config, factory, result

from tushare_downloader.apis import get_api
from tushare_downloader.download import execute
from tushare_downloader.reporting import JsonFiles, Reporter

pytestmark = pytest.mark.integration


def test_real_log_device_failure_after_commit_preserves_data(db, tmp_path, monkeypatch, capsys):
    db.initialize()
    original = JsonFiles.emit

    def fail_after_commit(self, record):
        if record.payload["event"] == "slice_result":
            self.stream.close()
            self.stream = open("/dev/full", "w")
        return original(self, record)

    monkeypatch.setattr(JsonFiles, "emit", fail_after_commit)
    code = execute(
        db,
        get_api("daily_basic"),
        "fetch",
        config(tmp_path),
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
        client_factory=factory([result(date(2024, 1, 2))]),
    )
    assert code == 1 and db.counts(get_api("daily_basic")) == (1, 0)
    assert "log is incomplete" in capsys.readouterr().err
    report = next((tmp_path / "reports").glob("*/report.md")).read_text()
    assert "1 non-empty" in report and "1 unattempted" in report
    assert "2024-01-02 | success" in report
    assert "2024-01-02 | unattempted" not in report


def test_before_report_failure_performs_no_requests(db, tmp_path, monkeypatch):
    db.initialize()
    original = Reporter.report

    def fail(self, name, *args, **kwargs):
        if name == "before":
            raise OSError("output unavailable")
        return original(self, name, *args, **kwargs)

    monkeypatch.setattr(Reporter, "report", fail)
    with pytest.raises(OSError):
        execute(
            db,
            get_api("daily_basic"),
            "fetch",
            config(tmp_path),
            start=date(2024, 1, 2),
            end=date(2024, 1, 2),
            client_factory=factory([]),
        )
    assert db.counts(get_api("daily_basic")) == (0, 0)


def test_interrupt_during_request_reports_failed_current_slice(db, tmp_path):
    db.initialize()

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, *args):
            raise KeyboardInterrupt

    code = execute(
        db,
        get_api("daily_basic"),
        "fetch",
        config(tmp_path),
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
        client_factory=Client,
    )
    assert code == 130
    report = next((tmp_path / "reports").glob("*/report.md")).read_text()
    assert "1 failed" in report and "1 unattempted" in report
    assert db.counts(get_api("daily_basic")) == (0, 0)


def test_sigkill_preserves_committed_data_and_unfinished_plan(db, tmp_path):
    import os
    import select
    import signal
    import subprocess
    import sys

    db.initialize()
    read_fd, write_fd = os.pipe()
    script = """
import os
import signal
from datetime import date
from decimal import Decimal
from pathlib import Path
import psycopg
from tushare_downloader.apis import get_api
from tushare_downloader.client import ApiResult
from tushare_downloader.config import Settings
from tushare_downloader.download import execute
from tushare_downloader.storage import Store
api = get_api('daily_basic')
class Client:
    def __init__(self, *args, **kwargs): self.calls = 0
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def query(self, *args):
        self.calls += 1
        if self.calls == 2:
            os.write(int(os.environ['READY_FD']), b'ready')
            signal.pause()
            raise AssertionError('Must be killed before second response')
        return ApiResult((('001.SZ', date(2024, 1, 2),
                           *[Decimal(1) for _ in api.fields[2:]]),), 1, 0, 1)
root = Path(os.environ['OUTPUT_DIR'])
with psycopg.connect(os.environ['TEST_DATABASE_URL'], autocommit=True) as conn:
    assert conn.info.dbname == conn.info.user == 'tushare_test'
    store = Store(conn)
    with store.writer():
        execute(store, api, 'fetch', Settings(token='fixture', plain=True,
            progress='off', log_dir=root/'logs', report_dir=root/'reports'),
            start=date(2024,1,2), end=date(2024,1,3), client_factory=Client)
"""
    env = dict(
        os.environ, TEST_DATABASE_URL=db.test_dsn, READY_FD=str(write_fd), OUTPUT_DIR=str(tmp_path)
    )
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        pass_fds=(write_fd,),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.close(write_fd)
    try:
        assert select.select([read_fd], [], [], 10)[0], "Child did not reach second request"
        assert os.read(read_fd, 5) == b"ready"
        assert db.counts(get_api("daily_basic")) == (1, 0)
        report_path = next((tmp_path / "reports").glob("*/report.md"))
        original = report_path.read_bytes()
        process.kill()
        assert process.wait(timeout=5) == -signal.SIGKILL
        assert report_path.read_bytes() == original
        assert b"Final result: not recorded" in original
        assert db.counts(get_api("daily_basic")) == (1, 0)
        assert db.conn.execute("SELECT trade_date FROM raw.daily_basic").fetchone()[0] == date(
            2024, 1, 2
        )
    finally:
        os.close(read_fd)
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
