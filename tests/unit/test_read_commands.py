import pytest
from click.testing import CliRunner

from tushare_downloader.cli import main


@pytest.mark.parametrize(
    "flags", [[], ["--plain"], ["-q"], ["-v"], ["--plain", "-q"], ["--plain", "-v"]]
)
def test_schema_is_offline_and_complete(flags, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PGPORT", "invalid-unrelated-setting")
    monkeypatch.setenv("TUSHARE_TOKEN", "private-token")
    result = CliRunner().invoke(main, [*flags, "schema", "daily"])
    assert result.exit_code == 0, result.output
    assert "Shipped schema contract" in result.output
    for text in ["raw.daily", "1.0.0", "trade_date", "numeric", "_is_stale", "_last_seen_at"]:
        assert text in result.output
    assert "private-token" not in result.output
    assert not list(tmp_path.iterdir())


def test_schema_index(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["schema"])
    assert result.exit_code == 0
    for api in ["daily", "daily_basic", "stock_basic", "adj_factor", "stk_limit", "suspend_d"]:
        assert "raw." + api in result.output


@pytest.mark.parametrize("command", ["schema", "inspect", "setup"])
def test_new_help_has_specific_examples(command):
    result = CliRunner().invoke(main, [command, "--help"])
    assert result.exit_code == 0, result.output
    assert "Examples:" in result.output
    assert "tushare-downloader " + command in result.output


def test_inspect_invalid_arguments_do_not_connect(monkeypatch):
    def no_connection(*a, **kw):
        pytest.fail("invalid argument connected to database")

    monkeypatch.setattr("tushare_downloader.cli.connect", no_connection)
    for arguments in [["inspect", "invalid"], ["inspect", "--counts"]]:
        result = CliRunner().invoke(main, arguments)
        assert result.exit_code == 2
        assert "No such command" not in result.output


def test_setup_noninteractive_fails_without_waiting():
    result = CliRunner().invoke(main, ["setup"])
    assert result.exit_code == 2
    assert "interactive terminal" in result.output


def test_inspect_displays_utc_regardless_of_server_timezone(monkeypatch, tmp_path):
    from datetime import datetime, timedelta, timezone

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "tushare_downloader.inspection.inspect_dataset",
        lambda *a, **kw: {
            "Dataset": "daily",
            "ok": True,
            "Last successful fetch (UTC)": datetime(
                2026, 8, 4, 8, tzinfo=timezone(timedelta(hours=8))
            ),
        },
    )
    result = CliRunner().invoke(main, ["--plain", "inspect", "daily"])
    assert result.exit_code == 0, result.output
    assert "2026-08-04T00:00:00Z" in result.output
    assert "+08:00" not in result.output
