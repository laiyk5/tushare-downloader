import json

import pytest
from click.testing import CliRunner

from tushare_downloader.apis import get_api
from tushare_downloader.cli import main
from tushare_downloader.config import ConfigError, Settings
from tushare_downloader.reporting import Reporter


@pytest.mark.parametrize("flags", [[], ["-q"], ["-v"], ["--plain"]])
def test_dataset_purpose_is_offline(flags, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, [*flags, "list"])
    assert result.exit_code == 0
    for text in [
        "Daily valuation and turnover indicators",
        "Stock listing and reference information",
        "Daily prices and trading volume",
        "Price adjustment factors",
        "Daily upper and lower price limits",
        "Trading suspension and resumption events",
    ]:
        assert text in result.output
    assert "stale reconciliation=" not in result.output
    assert result.output == CliRunner().invoke(main, [*flags, "ls"]).output


@pytest.mark.parametrize("flag", ["--plain", "-q", "-v", "--env-file=FAKE_SECRET", "--env-file"])
def test_misplaced_global_option(flag):
    result = CliRunner().invoke(main, ["inspect", "daily_basic", flag])
    assert result.exit_code == 2
    assert "global option" in result.output
    assert "before the command" in result.output
    assert "FAKE_SECRET" not in result.output
    if "env-file" in flag:
        assert "--env-file FILE" in result.output


@pytest.mark.parametrize("command", [[], ["fetch"], ["refresh"], ["update"]])
def test_quiet_help_explains_preview(command):
    result = CliRunner().invoke(main, [*command, "--help"])
    assert result.exit_code == 0
    assert (
        "retained" in result.output.lower()
        or "quiet" in result.output.lower()
        and "preview" in result.output.lower()
    )


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
def test_preparation_reason_persisted(level, tmp_path):
    config = Settings(
        log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", log_level=level, plain=True
    )
    with pytest.raises(ConfigError):
        with Reporter(config, get_api("daily_basic"), "fetch", quiet=True) as reporter:
            raise ConfigError("Remote requests require TUSHARE_TOKEN.")
    events = [json.loads(x) for x in reporter.log_path.read_text().splitlines()]
    errors = [e for e in events if e["event"] == "preparation_failed"]
    assert len(errors) == 1
    assert errors[0]["code"] == "missing_tushare_token"
    assert errors[0]["level"] == "ERROR"
    text = (reporter.folder / "report.md").read_text()
    assert "Set TUSHARE_TOKEN" in text
    assert "No blocks were attempted." in text
    assert "## Block details" not in text


@pytest.mark.parametrize(
    "config,dirty,expected",
    [
        ("not_saved", False, "no save needed"),
        ("not_saved", True, "Changes were not saved"),
        ("saved", True, "Saved"),
        ("failed", True, "failed"),
    ],
)
def test_setup_configuration_explanation(config, dirty, expected):
    from tushare_downloader.setup_presentation import configuration_result

    assert expected in configuration_result(config, dirty=dirty)


def test_login_explanation_preserves_failures():
    from tushare_downloader.setup_presentation import login_result

    assert login_result("reader", "not_checked") == "Reader login: Not tested in this run."
    assert login_result("writer", "verified") == "Writer login: Verified."
    assert "failed" in login_result("reader", "failed").lower()


@pytest.mark.parametrize("fault", ["secret", "log", "report"])
def test_safe_preparation_faults(fault, tmp_path, monkeypatch):
    import click

    from tushare_downloader.cli import guarded

    config = Settings(log_dir=tmp_path / "logs", report_dir=tmp_path / "reports", plain=True)

    @click.command()
    @click.pass_context
    def command(ctx):
        def action():
            with Reporter(config, get_api("daily_basic"), "fetch", verbose=1) as reporter:
                if fault == "log":
                    monkeypatch.setattr(
                        reporter.handler,
                        "emit",
                        lambda *a: (_ for _ in ()).throw(OSError("FAKE_PASSWORD")),
                    )
                if fault == "report":
                    monkeypatch.setattr(
                        reporter,
                        "report",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("FAKE_PASSWORD")),
                    )
                raise RuntimeError("postgresql://user:FAKE_PASSWORD@host/")

        guarded(ctx, action)

    result = CliRunner().invoke(command)
    assert result.exit_code == 1
    assert "FAKE_PASSWORD" not in result.output
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert "FAKE_PASSWORD" not in path.read_text()
    if fault == "secret":
        events = [
            json.loads(x)
            for x in next((tmp_path / "logs/fetch").glob("*.jsonl")).read_text().splitlines()
        ]
        assert sum(e["event"] == "preparation_failed" for e in events) == 1
        assert "preparation_error" in str(events)


@pytest.mark.parametrize(
    "args",
    [
        ["inspect", "daily_basic", "--plian"],
        ["inspect", "daily_basic", "-qv"],
        ["inspect", "--", "--plain"],
    ],
)
def test_no_guess_or_reparse(args):
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 2
    assert "global option" not in result.output


def test_legitimate_subcommand_options():
    result = CliRunner().invoke(main, ["inspect", "daily_basic", "-c", "--help"])
    assert result.exit_code == 0 and "global option" not in result.output


@pytest.mark.parametrize("width,flags", [(40, []), (80, ["--plain"]), (120, [])])
def test_dataset_widths(width, flags):
    result = CliRunner().invoke(main, [*flags, "list"], terminal_width=width)
    assert result.exit_code == 0
    rows = result.output.splitlines()
    assert len(rows) == 6
    assert all(
        name in result.output
        for name in ["daily_basic", "stock_basic", "daily:", "adj_factor", "stk_limit", "suspend_d"]
    )


def test_headless_and_environment_only_configuration_do_not_claim_a_file():
    from tushare_downloader.setup_presentation import configuration_result

    assert (
        configuration_result("not_saved", headless=True)
        == "Configuration: Unchanged (headless does not save settings)."
    )
    assert "file" not in configuration_result("not_saved", dirty=False).lower()


@pytest.mark.parametrize("state", ["failed", "unknown", "interrupted"])
def test_failed_logins_are_not_untested(state):
    from tushare_downloader.setup_presentation import login_result

    text = login_result("reader", state)
    assert state in text and "Not tested" not in text
