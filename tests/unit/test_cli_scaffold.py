from click.testing import CliRunner

from tushare_downloader.cli import main


def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "fetch/refresh/update" in result.output


def test_list_without_credentials(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "daily_basic: 只增型" in result.output
    assert runner.invoke(main, ["ls"]).output == result.output


def test_version():
    assert CliRunner().invoke(main, ["--version"]).exit_code == 0


def test_unimplemented_command():
    assert CliRunner().invoke(main, ["fetch", "daily_basic"]).exit_code == 2


def test_conflicting_verbosity():
    assert CliRunner().invoke(main, ["-q", "-v", "list"]).exit_code == 2
