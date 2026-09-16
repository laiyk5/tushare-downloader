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
