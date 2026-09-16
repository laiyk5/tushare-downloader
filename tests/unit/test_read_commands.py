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


def test_inspect_interrupt_retains_previous_results_and_exits_130(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls = []

    def inspect(settings, name, counts):
        calls.append(name)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return {"Dataset": name, "State": "Ready", "ok": True}

    monkeypatch.setattr("tushare_downloader.inspection.inspect_dataset", inspect)
    result = CliRunner().invoke(main, ["--plain", "inspect"])
    assert result.exit_code == 130, result.output
    assert len(calls) == 2
    assert calls[0] in result.stdout and "Ready" in result.stdout
    assert "interrupted" in result.stderr.lower()
    assert "Complete" not in result.output
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "flags", [[], ["-q"], ["-v"], ["--plain"], ["--plain", "-q"], ["--plain", "-v"]]
)
def test_inspect_history_warning_survives_output_modes(monkeypatch, tmp_path, flags):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "tushare_downloader.inspection.inspect_dataset",
        lambda *args: {
            "Dataset": "daily",
            "Installed schema": "1.0.0",
            "Recorded history compatibility": "Incompatible request spec versions",
            "Recorded spec versions": [("old",)],
            "ok": True,
        },
    )
    result = CliRunner().invoke(main, [*flags, "inspect", "daily"])
    assert result.exit_code == 0
    assert "Incompatible request spec versions" in result.output
    assert "1.0.0" in result.output
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "flags", [[], ["-q"], ["-v"], ["--plain"], ["--plain", "-q"], ["--plain", "-v"]]
)
def test_inspect_partial_result_is_nonzero_and_keeps_available_fields(monkeypatch, tmp_path, flags):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "tushare_downloader.inspection.inspect_dataset",
        lambda *args: {
            "Dataset": "daily",
            "State": "Partial inspection",
            "Latest data": "2026-08-03",
            "Storage bytes (total / table / indexes)": "Unavailable",
            "ok": False,
        },
    )
    result = CliRunner().invoke(main, [*flags, "inspect", "daily"])
    assert result.exit_code == 1
    assert "2026-08-03" in result.stdout and "Unavailable" in result.stdout
    assert "Partial inspection" in result.stderr
    assert not list(tmp_path.iterdir())
