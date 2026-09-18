import json
from contextlib import nullcontext

import pytest
from click.testing import CliRunner

from tushare_downloader import cli
from tushare_downloader.apis import get_api
from tushare_downloader.config import Settings

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("flags,dry", [([], False), (["-q"], False), ([], True)])
def test_public_missing_token_is_actionable_and_write_free(db, tmp_path, monkeypatch, flags, dry):
    db.initialize()
    config = Settings(
        token=None,
        log_dir=tmp_path / "logs",
        report_dir=tmp_path / "reports",
        plain=True,
        calendar_filter="basic",
    )
    monkeypatch.setattr(cli, "settings", lambda ctx: config)
    monkeypatch.setattr(cli, "connect", lambda cfg: nullcontext(db.conn))

    def forbidden(*a, **k):
        raise AssertionError("Unexpected remote request")

    monkeypatch.setattr("requests.sessions.Session.request", forbidden)
    result = CliRunner().invoke(
        cli.main,
        [
            *flags,
            "fetch",
            "daily_basic",
            "-s",
            "2026-01-05",
            "-e",
            "2026-01-05",
            *(["--dry-run"] if dry else []),
        ],
    )
    assert result.exit_code == (0 if dry else 2), result.output
    assert db.counts(get_api("daily_basic")) == (0, 0)
    assert db.conn.execute("SELECT count(*) FROM meta.slices").fetchone()[0] == 0
    events = [
        json.loads(x)
        for x in next((tmp_path / "logs/fetch").glob("*.jsonl")).read_text().splitlines()
    ]
    failures = [e for e in events if e["event"] == "preparation_failed"]
    if dry:
        assert failures == []
    else:
        assert len(failures) == 1 and failures[0]["calendar_requests"] == 0
        report = next((tmp_path / "reports").glob("*/report.md")).read_text()
        for output in (result.output, report, str(failures)):
            assert "Set TUSHARE_TOKEN" in output
        assert "No blocks were attempted." in report and "## Block details" not in report
