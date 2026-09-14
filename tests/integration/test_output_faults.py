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
    assert "日志不完整" in capsys.readouterr().err
    report = next((tmp_path / "reports").glob("*/report.md")).read_text()
    assert "Success非空 1" in report and "未尝试 1" in report
    assert "2024-01-02 | success" in report
    assert "2024-01-02 | 未尝试" not in report


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
    assert "Failed 1" in report and "未尝试 1" in report
    assert db.counts(get_api("daily_basic")) == (0, 0)
