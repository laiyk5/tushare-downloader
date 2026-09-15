import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.config import Settings
from tushare_downloader.reporting import Reporter


@pytest.mark.parametrize("command", ["fetch", "refresh", "update"])
@pytest.mark.parametrize(
    "plain,quiet,verbose",
    [(p, q, v) for p in (False, True) for q, v in [(False, 0), (True, 0), (False, 1)]],
)
def test_command_directory_and_rotation(tmp_path, capsys, command, plain, quiet, verbose):
    config = Settings(
        log_dir=tmp_path / "custom logs", report_dir=tmp_path / "reports", plain=plain
    )
    old = config.log_dir / "old.jsonl"
    old.parent.mkdir()
    old.write_bytes(b"historical bytes\n")
    with Reporter(config, get_api("daily"), command, quiet=quiet, verbose=verbose) as reporter:
        assert reporter.log_path.parent == config.log_dir / command
        assert reporter.folder.parent == config.report_dir
        assert reporter.folder.name == reporter.log_path.stem
        assert str(reporter.log_path) in capsys.readouterr().out
        reporter.handler.limit = 1
        reporter.event("fixture")
        reporter.report("after", "Completed", ["fixture"])
        report = (reporter.folder / "report.md").read_text()
        for path in reporter.log_path.parent.glob("*.jsonl"):
            assert str(path) in report
            for line in path.read_text().splitlines():
                json.loads(line)
    assert old.read_bytes() == b"historical bytes\n"
    assert set(p.name for p in config.log_dir.iterdir()) == {"old.jsonl", command}


def test_command_directory_obstruction(tmp_path):
    config = Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports")
    config.log_dir.mkdir()
    (config.log_dir / "fetch").write_text("keep")
    with pytest.raises(OSError):
        Reporter(config, get_api("daily"), "fetch")
    assert (config.log_dir / "fetch").read_text() == "keep"


def test_unknown_command_cannot_escape_root(tmp_path):
    config = Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports")
    with pytest.raises(ValueError):
        Reporter(config, get_api("daily"), "../outside")
    assert not config.report_dir.exists()


def test_orphan_log_collision_is_not_overwritten(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    import tushare_downloader.reporting as reporting

    fixed = datetime(2026, 9, 15, tzinfo=UTC)
    monkeypatch.setattr(reporting, "datetime", SimpleNamespace(now=lambda tz: fixed))
    monkeypatch.setattr(reporting, "uuid4", lambda: SimpleNamespace(hex="12345678"))
    config = Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports")
    path = config.log_dir / "fetch" / "20260915T000000Z-12345678.jsonl"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"orphan")
    with pytest.raises(FileExistsError):
        Reporter(config, get_api("daily"), "fetch")
    assert path.read_bytes() == b"orphan"


def test_parallel_calls_keep_independent_logs(tmp_path):
    config = Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports")

    def run(api):
        with Reporter(config, get_api(api), "fetch") as reporter:
            return reporter.log_path

    with ThreadPoolExecutor(max_workers=2) as pool:
        paths = list(pool.map(run, ["daily", "stock_basic"]))
    assert len(set(paths)) == 2
    assert all(p.parent == config.log_dir / "fetch" and p.is_file() for p in paths)
