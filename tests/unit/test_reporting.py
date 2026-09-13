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
        assert "另有 2 条" in output and "third" not in output
        text = (reporter.folder / "before.md").read_text()
        assert "third" in text and "fourth" in text
        assert not (reporter.folder / "before.tmp").exists()
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
        reporter.report("after", "结果", ["存在失败"], explicit=True)
        assert "存在失败" in capsys.readouterr().out
    finally:
        reporter.close()
