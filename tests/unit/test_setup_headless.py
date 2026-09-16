"""H01/H04/H07 public CLI boundaries; no real database accessed here."""

import pytest
from click.testing import CliRunner

from tushare_downloader.cli import main


def test_help_has_headless_and_no_connection_dependency():
    result = CliRunner().invoke(main, ["setup", "--help"])
    assert result.exit_code == 0
    assert "--headless" in result.output
    assert "--credentials-file" in result.output


def test_apply_requires_headless():
    result = CliRunner().invoke(main, ["setup", "--apply"])
    assert result.exit_code == 2
    assert "--headless" in result.output


def test_headless_token_only_needs_configuration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text("TUSHARE_TOKEN=SECRET\n")
    result = CliRunner().invoke(main, ["setup", "--headless"])
    assert result.exit_code == 4
    assert "SECRET" not in result.output
    assert "Needs configuration" in result.output


def test_explicit_missing_config_is_input_error(tmp_path):
    result = CliRunner().invoke(main, ["-c", str(tmp_path / "missing"), "setup", "--headless"])
    assert result.exit_code == 2


def test_headless_check_never_calls_apply(tmp_path, monkeypatch):
    import tushare_downloader.setup_headless as module

    monkeypatch.chdir(tmp_path)
    for key in ("PGHOST", "PGDATABASE", "PGUSER"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / ".env"
    original = "PGHOST=localhost\nPGDATABASE=example\nPGUSER=writer\n"
    path.write_text(original)

    class Fake:
        def __init__(self, *args, **kwargs):
            self.log = type("Log", (), {"path": tmp_path / "events.jsonl"})()

        def inspect(self):
            return {"readiness": "needs_configuration", "actions": ["grants"]}

        def apply(self):
            raise AssertionError("Check must never apply")

        def close(self):
            pass

        def finish_check(self, code):
            return {"exit_code": code}

    monkeypatch.setattr(module, "SetupSession", Fake)
    result = CliRunner().invoke(main, ["--plain", "setup", "--headless"])
    assert result.exit_code == 4, result.output
    assert path.read_text() == original


def test_interactive_plain_rejected_before_opening_ui(tmp_path, monkeypatch):
    import sys

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    result = CliRunner().invoke(main, ["--plain", "setup"])
    assert result.exit_code == 2
    assert "plain" in result.output.lower()


def test_setup_entry_uses_native_ui_adapter(tmp_path, monkeypatch):
    import tushare_downloader.cli as cli
    import tushare_downloader.setup_tui as tui

    calls = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "setup_terminal_available", lambda: True, raising=False)
    monkeypatch.setattr(tui, "run_tui", lambda ctx: calls.append("native"), raising=False)
    result = CliRunner().invoke(main, ["setup"])
    assert result.exit_code == 0, result.output
    assert calls == ["native"]


def test_headless_url_only_explains_supported_keys_without_echoing_secret(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in list(__import__("os").environ):
        if key.startswith("PG") or key == "DATABASE_URL":
            monkeypatch.delenv(key, raising=False)
    path = tmp_path / ".env"
    original = "DATABASE_URL=SECRET\n"
    path.write_text(original)
    result = CliRunner().invoke(main, ["setup", "--headless"])
    assert result.exit_code == 4
    assert "DATABASE_URL is not supported" in result.output
    assert "SECRET" not in result.output
    assert path.read_text() == original


def test_mid_execution_log_failure_stops_writes_and_reports_known_results_on_stderr(
    tmp_path, monkeypatch
):
    import os
    from copy import deepcopy

    from tushare_downloader import setup_headless
    from tushare_downloader.setup_events import SetupLog
    from tushare_downloader.setup_service import SetupSession

    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith(("PG", "SETUP_")):
            monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text("PGHOST=localhost\nPGDATABASE=example\nPGUSER=writer\n")
    state = dict(
        kind="managed",
        roles_safe=True,
        writer_exists=True,
        reader_exists=True,
        grants_needed=True,
        missing=["daily"],
        database_id="fixture",
    )
    writes = []

    class Backend:
        def inspect(self, *args):
            return deepcopy(state)

        def apply(self, expected, action, *args):
            writes.append(action)
            state["missing"] = []
            return deepcopy(state)

    monkeypatch.setattr(
        setup_headless,
        "SetupSession",
        lambda *args, **kwargs: SetupSession(*args, backend=Backend(), **kwargs),
    )
    emit = SetupLog.emit

    def failing_emit(self, event, **kwargs):
        if event in {"step_finished", "session_finished"}:
            raise OSError("SECRET simulated disk error")
        return emit(self, event, **kwargs)

    monkeypatch.setattr(SetupLog, "emit", failing_emit)
    result = CliRunner().invoke(main, ["setup", "--headless", "--apply"])
    assert result.exit_code == 1
    assert writes == ["initialize"]
    assert "Completed: initialize" in result.stderr
    assert "Not attempted: grants" in result.stderr
    assert "log_failed" in result.stderr
    assert "SECRET" not in result.output


def test_headless_rejects_multi_host_before_session_creation(tmp_path, monkeypatch):
    import tushare_downloader.setup_headless as module

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PGHOST", "first,second")
    monkeypatch.setenv("PGDATABASE", "example")
    monkeypatch.setenv("PGUSER", "writer")

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid target must not create a session")

    monkeypatch.setattr(module, "SetupSession", forbidden)
    result = CliRunner().invoke(main, ["setup", "--headless"])
    assert result.exit_code == 2, result.output
    assert "one server host" in result.output


@pytest.mark.parametrize(
    "args,plain,terminal",
    [
        (["setup", "--apply"], "false", True),
        (["setup", "--credentials-file", "missing.json"], "false", True),
        (["--plain", "setup"], "false", True),
        (["setup"], "true", True),
        (["setup"], "false", False),
    ],
)
def test_invalid_setup_mode_never_opens_app_or_prompts(
    tmp_path, monkeypatch, args, plain, terminal
):
    from tushare_downloader import cli, setup_tui

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PLAIN", plain)
    monkeypatch.setattr(cli, "setup_terminal_available", lambda: terminal)

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid mode must not open the native app")

    monkeypatch.setattr(setup_tui, "SetupApp", forbidden)
    result = CliRunner().invoke(main, args, input="")
    assert result.exit_code == 2, result.output
    assert "headless" in result.output.lower()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["setup", "--help"],
        ["setup", "--apply", "--help"],
        ["setup", "--credentials-file", "missing.json", "--help"],
    ],
)
def test_help_does_not_read_configuration_or_credentials(tmp_path, monkeypatch, args):
    from tushare_downloader import setup_config, setup_credentials

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PGPORT", "invalid")

    def forbidden(*args, **kwargs):
        raise AssertionError("Help must not read configuration or credentials")

    monkeypatch.setattr(setup_config, "read_config", forbidden)
    monkeypatch.setattr(setup_credentials, "load_credentials", forbidden)
    result = CliRunner().invoke(main, args, input="")
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "input_tty,output_tty,term,expected",
    [
        (True, True, "xterm-256color", True),
        (False, True, "xterm", False),
        (True, False, "xterm", False),
        (True, True, "dumb", False),
    ],
)
def test_terminal_gate_checks_both_streams_and_term(
    monkeypatch, input_tty, output_tty, term, expected
):
    from tushare_downloader import cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: input_tty)
    monkeypatch.setattr(cli.sys.stdout, "isatty", lambda: output_tty)
    monkeypatch.setenv("TERM", term)
    assert cli.setup_terminal_available() is expected


def test_log_close_failure_returns_safe_error_without_losing_summary(tmp_path, monkeypatch):
    from tushare_downloader import setup_headless
    from tushare_downloader.setup_events import SetupLog
    from tushare_downloader.setup_service import SetupSession

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGDATABASE", "fixture")
    monkeypatch.setenv("PGUSER", "writer")

    class Backend:
        def inspect(self, *args):
            return dict(
                kind="managed",
                roles_safe=True,
                writer_exists=True,
                reader_exists=True,
                missing=[],
                grants_needed=False,
            )

    monkeypatch.setattr(
        setup_headless,
        "SetupSession",
        lambda *args, **kwargs: SetupSession(*args, backend=Backend(), **kwargs),
    )
    original = SetupLog.close

    def failed_close(self):
        original(self)
        raise OSError("SECRET close failure")

    monkeypatch.setattr(SetupLog, "close", failed_close)
    result = CliRunner().invoke(main, ["setup", "--headless"])
    assert result.exit_code == 1
    assert "Ready" in result.stdout
    assert "log could not be closed" in result.stderr
    assert "SECRET" not in result.output
    assert isinstance(result.exception, SystemExit)
