"""Packaging/entry-point checks only; no assertions about future business features."""

from importlib.metadata import version

from click.testing import CliRunner

from tushare_downloader.cli import main


def test_help_needs_no_token_or_database(monkeypatch):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    monkeypatch.delenv("PGPASSWORD", raising=False)
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "not" in result.output and "implemented" in result.output


def test_version_matches_package_metadata():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert version("tushare-downloader") in result.output


def test_unimplemented_command_is_not_reported_as_success():
    result = CliRunner().invoke(main, ["fetch", "daily_basic"])
    assert result.exit_code == 2
