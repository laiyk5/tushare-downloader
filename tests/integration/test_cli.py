import psycopg
import pytest
from click.testing import CliRunner

from tushare_downloader import cli
from tushare_downloader.config import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def runner(db, tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli,
        "settings",
        lambda ctx: Settings(
            log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", plain=True
        ),
    )
    monkeypatch.setattr(
        cli, "connect", lambda settings: psycopg.connect(db.conn.info.dsn, autocommit=True)
    )
    return CliRunner()


def test_cli_init_preview_dry_run(db, runner):
    result = runner.invoke(cli.main, ["init"])
    assert result.exit_code == 0, result.output
    assert runner.invoke(cli.main, ["init-db"]).exit_code == 0
    result = runner.invoke(
        cli.main, ["f", "daily_basic", "-s", "2024-01-02", "-e", "2024-01-03", "--dry-run"]
    )
    assert result.exit_code == 0, result.output
    assert "未请求远端" in result.output
    result = runner.invoke(cli.main, ["clean", "daily_basic"])
    assert result.exit_code == 0 and "未删除" in result.output
    result = runner.invoke(
        cli.main, ["clean", "daily_basic", "--apply", "--confirm-database", "tushare"]
    )
    assert result.exit_code == 1


def test_cli_busy_exit_code(db, runner):
    db.initialize()
    with db.writer():
        result = runner.invoke(cli.main, ["init"])
    assert result.exit_code == 3, result.output


@pytest.mark.parametrize(
    "args",
    [
        ["fetch", "daily_basic"],
        ["fetch", "daily_basic", "-s", "2024-01-03", "-e", "2024-01-02"],
        ["refresh", "stock_basic", "-s", "2024-01-02", "-e", "2024-01-03"],
        ["refresh", "daily_basic", "-s", "2024-01-02", "-e", "2024-01-02", "--max-age", "bad"],
    ],
)
def test_invalid_semantics_are_usage_errors(runner, args):
    assert runner.invoke(cli.main, args).exit_code == 2
