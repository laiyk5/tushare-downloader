"""H01/H04/H07 public CLI boundaries; no real database accessed here."""

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
