import io
import os
import threading
from dataclasses import replace
from datetime import date, timedelta

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.config import Settings
from tushare_downloader.reporting import RangeDetail, Reporter, merge_ranges


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def reporter(tmp_path):
    clock = Clock()
    result = Reporter(
        Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", plain=True),
        get_api("daily_basic"),
        "fetch",
        clock=clock,
    )
    yield result, clock
    result.close()


def test_eta_threshold_recent_samples_and_retry_suppression(reporter):
    result, clock = reporter
    result.total = 10
    for i in range(4):
        result.begin_slice("range")
        clock.now += 2
        result.advance(i + 1, 10, 100, 1, 0)
    assert result.snapshot()["eta"] is None
    result.begin_slice("range")
    clock.now += 2
    result.advance(5, 10, 100, 1, 0)
    assert result.snapshot()["eta"] == 10
    result.phase("重试等待")
    assert result.snapshot()["eta"] is None
    result.phase("合并提交")
    assert result.snapshot()["eta"] is None


def test_stalled_request_does_not_keep_optimistic_eta(reporter):
    result, clock = reporter
    result.total = 10
    result.samples.extend([2] * 5)
    result.done = 5
    result.begin_slice("range")
    clock.now += 7
    assert result.snapshot()["eta"] is None


def test_progress_updates_during_http_without_commits(reporter, monkeypatch):
    result, clock = reporter
    output = []
    observed = threading.Event()

    def echo(text, **kwargs):
        if kwargs.get("err"):
            output.append(text)
            observed.set()

    monkeypatch.setattr("tushare_downloader.reporting.click.echo", echo)
    result.begin(1)
    result.begin_slice("当前全集")
    result.phase("HTTP 请求")
    result.attempt()
    result.receive(200)
    clock.now = 6
    assert observed.wait(2)
    result.stop_progress()
    assert any("已取得/暂存 200 行" in line and "已确认入库输入 0 行" in line for line in output)
    assert result.worker is None
    count = len(output)
    # No background worker remains that could append after the final report.
    assert result.stop_event.is_set() and len(output) == count


def test_merge_adjacent_only_with_same_reason():
    day = date(2024, 1, 1)
    values = [
        RangeDetail(day, day, "network"),
        RangeDetail(day + timedelta(days=1), day + timedelta(days=1), "network"),
        RangeDetail(day + timedelta(days=2), day + timedelta(days=2), "permission"),
        RangeDetail(day + timedelta(days=4), day + timedelta(days=4), "permission"),
    ]
    result = merge_ranges(values)
    assert [x.count for x in result] == [2, 1, 1]
    assert result[0].end == day + timedelta(days=1)


def test_section_budgets_preserve_summary_and_each_category(reporter, capsys, monkeypatch):
    result, _ = reporter
    result.settings = replace(result.settings, report_max_items=1)
    monkeypatch.setattr("shutil.get_terminal_size", lambda *args: os.terminal_size((40, 24)))
    days = [date(2024, 1, 1) + timedelta(days=2 * i) for i in range(3)]
    sections = [
        ("失败", [RangeDetail(day, day, "network") for day in days]),
        ("空响应", [RangeDetail(days[0], days[0], "empty")]),
    ]
    result.report("after", "结果", ["summary1", "summary2", "summary3"], sections=sections)
    output = capsys.readouterr().out
    assert "summary3" in output and "失败" in output and "空响应" in output
    assert "另有 2 个范围" in output
    assert "\x1b" not in output
    text = (result.folder / "after.md").read_text()
    assert all(str(day) in text for day in days)
    assert "  network" in output


@pytest.mark.parametrize("quiet,progress", [(True, "auto"), (False, "off")])
def test_disabled_progress_has_no_thread(reporter, quiet, progress):
    result, _ = reporter
    result.quiet = quiet
    result.settings = replace(result.settings, progress=progress)
    result.begin(10)
    assert result.worker is None


def test_rich_progress_uses_stderr_and_stops(reporter, monkeypatch):
    class TTY(io.StringIO):
        def isatty(self):
            return True

    result, clock = reporter
    result.settings = replace(result.settings, plain=False)
    output = TTY()
    monkeypatch.setattr("sys.stderr", output)
    result.begin(2)
    result.begin_slice("range")
    result.phase("HTTP 请求")
    clock.now = 2
    result.advance(1, 2, 10, 1, 0)
    result.stop_progress()
    assert result.progress is None and result.worker is None
    assert "HTTP" in output.getvalue()


def test_no_final_report_if_atomic_replace_fails(reporter, monkeypatch):
    result, _ = reporter

    def fail(*args):
        raise OSError("simulated")

    monkeypatch.setattr("pathlib.Path.replace", fail)
    with pytest.raises(OSError):
        result.report("after", "结果", ["not-final"], sections=[])
    assert not (result.folder / "after.md").exists()
