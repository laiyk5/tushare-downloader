import json
import logging

from tushare_downloader.apis import get_api
from tushare_downloader.config import Settings
from tushare_downloader.reporting import JsonFiles, Reporter


def test_full_report_survives_terminal_truncation(tmp_path, capsys):
    settings = Settings(
        log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", report_max_items=2, plain=True
    )
    reporter = Reporter(settings, get_api("daily_basic"), "fetch")
    try:
        reporter.report("before", "计划", ["first", "second", "third", "fourth"])
        output = capsys.readouterr().out
        assert "2 more items" in output and "third" not in output
        text = (reporter.folder / "report.md").read_text()
        assert "third" in text and "fourth" in text
        assert not (reporter.folder / "report.tmp").exists()
    finally:
        reporter.close()


def test_rotation_preserves_all_events(tmp_path):
    handler = JsonFiles(tmp_path / "run.jsonl", limit=120)
    logger = logging.Logger("rotation")
    logger.addHandler(handler)
    try:
        for i in range(20):
            logger.info("event", extra={"payload": {"event": "test", "sequence": i}})
    finally:
        handler.close()
    events = [
        json.loads(line) for p in tmp_path.glob("*.jsonl") for line in p.read_text().splitlines()
    ]
    assert sorted(e["sequence"] for e in events) == list(range(20))


def test_quiet_retains_warning_report_and_paths(tmp_path, capsys):
    reporter = Reporter(
        Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports"),
        get_api("daily_basic"),
        "fetch",
        quiet=True,
    )
    try:
        reporter.report("after", "结果", ["存在Failed"], explicit=True)
        assert "存在Failed" in capsys.readouterr().out
    finally:
        reporter.close()


def test_single_report_retains_plan_when_final_replace_fails(tmp_path, monkeypatch):
    from pathlib import Path

    import pytest

    reporter = Reporter(
        Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports"),
        get_api("daily_basic"),
        "fetch",
    )
    try:
        path = reporter.report("before", "Plan", ["Range: original", "Source: a|b<c>"])
        original = path.read_text()
        assert "Final result: not recorded" in original
        assert "a&#124;b&lt;c&gt;" in original
        replace = Path.replace

        def fail(*args):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(Path, "replace", fail)
        with pytest.raises(OSError):
            reporter.report("after", "Completed", ["Committed: 10"])
        assert path.read_text() == original
        monkeypatch.setattr(Path, "replace", replace)
        final = reporter.report("after", "Completed", ["Committed: 10"])
        assert final == path
        text = final.read_text()
        assert "Original plan" in text and "original" in text and "Committed" in text
        assert "Final result: not recorded" not in text
        assert list(reporter.folder.glob("*.md")) == [path]
    finally:
        reporter.close()


def test_log_path_precedes_preparation_failure(tmp_path, capsys):
    import pytest

    with pytest.raises(RuntimeError):
        with Reporter(
            Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports"),
            get_api("stock_basic"),
            "fetch",
        ) as reporter:
            output = capsys.readouterr().out
            assert output.startswith("Log: ")
            assert reporter.log_path.is_file()
            raise RuntimeError("secret must not be printed")
    output = capsys.readouterr().out
    assert "Preparation failed" in output
    text = (reporter.folder / "report.md").read_text()
    assert "secret" not in text
    assert reporter.handler.stream.closed


def test_recent_activity_is_bounded_independent_of_log_level(tmp_path):
    reporter = Reporter(
        Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", terminal_log_lines=2),
        get_api("daily_basic"),
        "fetch",
        verbose=1,
    )
    try:
        for number in range(10):
            reporter.event("http_attempt", sequence=number)
        reporter.event("phase", level=logging.DEBUG, stage="request")
        assert len(reporter.recent) == 2
        assert "phase" in reporter.recent[-1]
        entries = [json.loads(line) for line in reporter.log_path.read_text().splitlines()]
        assert len([e for e in entries if e["event"] == "http_attempt"]) == 10
        assert not any(e["event"] == "phase" for e in entries)
    finally:
        reporter.close()


def test_terminal_controls_removed_and_markup_preserved():
    from tushare_downloader.reporting import terminal_text

    assert terminal_text("[red]source[/red]\x1b[2J\r\x07") == "[red]source[/red]"
    assert terminal_text("a\x1b]0;fake title\x07b") == "ab"


def test_empty_plan_reports_no_remote_check(tmp_path, monkeypatch, capsys):
    from tushare_downloader.download import execute

    class Store:
        def validate(self, api):
            pass

        def counts(self, api):
            return 5911, 0

    monkeypatch.setattr("tushare_downloader.download.plan", lambda *a: [])
    settings = Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", plain=True)
    assert execute(Store(), get_api("stock_basic"), "fetch", settings) == 0
    output = capsys.readouterr().out
    assert "Nothing to download" in output and "Data requests: 0" in output
    assert "Lookback" not in output and "Max age" not in output
    assert "Inserted:" not in output


def test_quiet_failure_is_compact_but_full_report_retained(tmp_path, capsys):
    reporter = Reporter(
        Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports"),
        get_api("daily_basic"),
        "fetch",
        quiet=True,
    )
    try:
        reporter.report(
            "after",
            "Result",
            [
                "Completed with failures",
                "Blocks: 1 failed",
                "Inserted: 125",
                "Updated: 200",
                "Retry failed ranges with fetch.",
            ],
            explicit=True,
        )
        output = capsys.readouterr().out
        assert "Blocks: 1 failed" in output and "Retry" in output
        assert "Inserted: 125" not in output
        assert "125" in (reporter.folder / "report.md").read_text()
    finally:
        reporter.close()


def test_report_includes_parts_created_by_final_log_events(tmp_path):
    reporter = Reporter(
        Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports"),
        get_api("daily_basic"),
        "fetch",
    )
    reporter.handler.limit = 150
    reporter.report("after", "Completed", ["Result: completed"])
    for i in range(10):
        reporter.event("coverage_after", scope=str(i))
    reporter.close()
    text = (reporter.folder / "report.md").read_text()
    assert reporter.handler.part > 0
    for path in (tmp_path / "logs").glob("*.jsonl"):
        import re
        from urllib.parse import unquote

        targets = {
            (reporter.folder / unquote(link)).resolve()
            for link in re.findall(r"\]\(([^)]+)\)", text)
        }
        assert path.resolve() in targets
