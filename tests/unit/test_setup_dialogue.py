"""Revision 4 entry and sequential-dialogue acceptance cases."""

import sys
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from tushare_downloader.cli import main


@pytest.mark.parametrize("args,new", [(["setup", "--new"], True), (["--plain", "setup"], False)])
def test_dialogue_entry_accepts_new_and_plain(tmp_path, monkeypatch, args, new):
    import tushare_downloader.cli as cli

    calls = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "setup_terminal_available", lambda: True)
    monkeypatch.setitem(
        sys.modules,
        "tushare_downloader.setup_dialogue",
        SimpleNamespace(run_dialogue=lambda ctx, new=False: calls.append((new, ctx.obj["plain"]))),
    )
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 0, result.output
    assert calls == [(new, "--plain" in args)]


def test_new_headless_conflict_is_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["setup", "--new", "--headless"])
    assert result.exit_code == 2
    assert "cannot be used with --headless" in result.output
    assert not (tmp_path / "logs").exists()


@pytest.mark.parametrize("state,code", [("ready", 0), ("unknown", 1), ("unsupported", 5)])
def test_ready_exits_without_questions_and_errors_keep_status(tmp_path, monkeypatch, state, code):
    import tushare_downloader.cli as cli
    import tushare_downloader.setup_dialogue as dialogue

    monkeypatch.chdir(tmp_path)
    for key in list(__import__("os").environ):
        if key.startswith(("PG", "SETUP_")) or key in {"PLAIN", "LOG_DIR"}:
            monkeypatch.delenv(key)
    (tmp_path / ".env").write_text("PGHOST=localhost\nPGDATABASE=fixture\nPGUSER=writer\n")
    calls = []

    class Session:
        def __init__(self, settings, reader, credentials, **kwargs):
            self.settings = settings
            self.reader = reader
            self.result = {}
            self.verification_pending = False
            self.actions = []
            self.readiness = state
            calls.append(settings.pg_host)

        def inspect(self):
            return {"readiness": state, "actions": [], "facts": {}, "reason_code": None}

        def close(self):
            pass

    monkeypatch.setattr(cli, "setup_terminal_available", lambda: True)
    monkeypatch.setattr(dialogue, "SetupSession", Session)
    result = CliRunner().invoke(main, ["--plain", "setup"], input="q\n")
    assert result.exit_code == code, result.output
    assert calls == ["localhost"]
    assert "Server host" not in result.output
    assert "Password" not in result.output
    assert "\x1b" not in result.output
    assert (
        tmp_path / ".env"
    ).read_text() == "PGHOST=localhost\nPGDATABASE=fixture\nPGUSER=writer\n"


def configure(tmp_path, monkeypatch, content=None):
    import os

    import tushare_downloader.cli as cli

    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith(("PG", "SETUP_")) or key in {"PLAIN", "LOG_DIR", "DATABASE_URL"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(cli, "setup_terminal_available", lambda: True)
    if content is not None:
        (tmp_path / ".env").write_text(content)


def test_explicit_edit_beats_environment_and_discards_old_password(tmp_path, monkeypatch):
    import click

    from tushare_downloader.setup_dialogue import FIELDS, Dialogue

    configure(tmp_path, monkeypatch, "PGHOST=file_host\nPGPASSWORD=OLD_SECRET\n")
    monkeypatch.setenv("PGHOST", "environment_host")
    seen = {}

    @click.command()
    @click.pass_context
    def entry(ctx):
        ctx.obj = {"plain": True}
        app = Dialogue(ctx)
        try:
            assert app.source()
            seen["initial"] = app.values["PGHOST"]
            app.field(FIELDS[0])
            seen["selected"] = app.values["PGHOST"]
            seen["secret"] = app.values.get("PGPASSWORD")
            seen["env"] = app.environment["PGHOST"]
        finally:
            app.log.close()

    result = CliRunner().invoke(entry, input="selected_host\n")
    assert result.exit_code == 0, result.output
    assert seen == {
        "initial": "environment_host",
        "selected": "selected_host",
        "secret": None,
        "env": "environment_host",
    }
    assert "OLD_SECRET" not in result.output


@pytest.mark.parametrize("existing", [True, False])
def test_new_connection_destination_and_secret_isolation(tmp_path, monkeypatch, existing):
    import click

    from tushare_downloader.setup_dialogue import Dialogue

    configure(tmp_path, monkeypatch)
    path = tmp_path / "chosen.env"
    original = "PGHOST=file_host\nPGPASSWORD=FILE_SECRET\n"
    if existing:
        path.write_text(original)
        (tmp_path / ".env.new").write_text("reserved")
    monkeypatch.setenv("PGPASSWORD", "ENV_SECRET")
    monkeypatch.setenv("PGHOST", "environment_host")
    seen = {}

    @click.command()
    @click.pass_context
    def entry(ctx):
        ctx.obj = {"plain": True, "env_file": path}
        app = Dialogue(ctx, new=True)
        try:
            assert app.source()
            seen.update(path=app.path, password=app.values.get("PGPASSWORD"), dirty=app.dirty)
        finally:
            app.log.close()

    result = CliRunner().invoke(entry)
    assert result.exit_code == 0, result.output
    assert seen == {
        "path": tmp_path / ".env.new.1" if existing else path,
        "password": None,
        "dirty": True,
    }
    assert path.read_text() == original if existing else not path.exists()
    assert "SECRET" not in result.output


@pytest.mark.parametrize("input_text,expected", [("q\n", 2), ("p\nvalid.env\n", 0)])
def test_bad_explicit_config_is_not_silently_ignored(tmp_path, monkeypatch, input_text, expected):
    import click

    from tushare_downloader.setup_dialogue import Dialogue

    configure(tmp_path, monkeypatch, "PGHOST=one\nPGHOST=two\n")
    (tmp_path / "valid.env").write_text("PGHOST=valid\n")

    @click.command()
    @click.pass_context
    def entry(ctx):
        ctx.obj = {"plain": True, "env_file": tmp_path / ".env"}
        app = Dialogue(ctx)
        try:
            if not app.source():
                ctx.exit(app.code)
            assert app.values["PGHOST"] == "valid"
        finally:
            if app.log:
                app.log.close()

    result = CliRunner().invoke(entry, input=input_text)
    assert result.exit_code == expected, result.output
    assert (tmp_path / ".env").read_text() == "PGHOST=one\nPGHOST=two\n"


def test_eof_in_first_prompt_is_130_without_database_write(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    result = CliRunner().invoke(main, ["--plain", "setup"], input="")
    assert result.exit_code == 130, result.output
    assert "Interrupted" in result.output
    assert not (tmp_path / ".env").exists()


def test_ready_full_environment_does_not_create_file(tmp_path, monkeypatch):
    import tushare_downloader.setup_dialogue as dialogue

    configure(tmp_path, monkeypatch)
    for key, value in {"PGHOST": "localhost", "PGDATABASE": "fixture", "PGUSER": "writer"}.items():
        monkeypatch.setenv(key, value)

    class Ready:
        def __init__(self, settings, reader, credentials, **kwargs):
            self.settings, self.reader = settings, reader
            self.readiness = "ready"

        def inspect(self):
            return {"readiness": "ready", "actions": [], "facts": {}}

        def close(self):
            pass

    monkeypatch.setattr(dialogue, "SetupSession", Ready)
    result = CliRunner().invoke(main, ["--plain", "setup"])
    assert result.exit_code == 0, result.output
    assert "Choice" not in result.output
    assert not (tmp_path / ".env").exists()


def install_backend(monkeypatch, backend):
    from tushare_downloader import setup_dialogue
    from tushare_downloader.setup_service import SetupSession

    monkeypatch.setattr(
        setup_dialogue,
        "SetupSession",
        lambda *a, **kw: SetupSession(*a, **kw, backend=backend),
    )


class DialogueBackend:
    def __init__(self, *, missing=None, grants=False, verification_failure=False):
        self.state = dict(
            kind="managed",
            roles_safe=True,
            writer_exists=True,
            reader_exists=True,
            grants_needed=grants,
            missing=missing or [],
            database_id="fixture",
        )
        self.writes = []
        self.verified = 0
        self.verification_failure = verification_failure

    def inspect(self, *args):
        from copy import deepcopy

        return deepcopy(self.state)

    def apply(self, expected, action, *args):
        self.writes.append(action)
        if action == "initialize":
            self.state["missing"] = []
        if action == "grants":
            self.state["grants_needed"] = False
        return self.inspect()

    def verify(self, *args):
        self.verified += 1
        return {
            "writer": "verified",
            "reader": "failed" if self.verification_failure and self.verified == 1 else "verified",
        }


BASE = "PGHOST=localhost\nPGDATABASE=fixture\nPGUSER=writer\n"


@pytest.mark.parametrize("confirmation", ["fixture", "wrong"])
def test_apply_requires_exact_target_and_preserves_plan(tmp_path, monkeypatch, confirmation):
    configure(tmp_path, monkeypatch, BASE)
    backend = DialogueBackend(missing=["daily"])
    install_backend(monkeypatch, backend)
    result = CliRunner().invoke(main, ["--plain", "setup"], input="c\n" + confirmation + "\nq\n")
    assert result.exit_code == 0, result.output
    assert backend.writes == (["initialize"] if confirmation == "fixture" else [])
    assert (tmp_path / ".env").read_text() == BASE


def test_failed_access_verification_retries_only_logins(tmp_path, monkeypatch):
    import json

    configure(tmp_path, monkeypatch, BASE)
    backend = DialogueBackend(grants=True, verification_failure=True)
    install_backend(monkeypatch, backend)
    # Review, decline admin override, keep reader auth, confirm; retry only reader secret.
    result = CliRunner().invoke(
        main, ["--plain", "setup"], input="c\nn\nk\nfixture\nr\nk\nr\nREADER_SECRET\n"
    )
    assert result.exit_code == 0, result.output
    assert backend.writes == ["grants"]
    assert backend.verified == 2
    assert "READER_SECRET" not in result.output
    events = [
        json.loads(line)
        for f in (tmp_path / "logs/setup").glob("*.jsonl")
        for line in f.read_text().splitlines()
    ]
    assert sum(e["event"] == "session_finished" for e in events) == 1
    assert events[-1]["exit_code"] == 0
    assert any(e["event"] == "verification_finished" and e["outcome"] == "failed" for e in events)
    assert "READER_SECRET" not in str(events)


@pytest.mark.parametrize("save_response", ["n", "y"])
def test_separate_save_keeps_database_untouched(tmp_path, monkeypatch, save_response):
    from tushare_downloader import setup_dialogue

    configure(tmp_path, monkeypatch, BASE)
    backend = DialogueBackend()
    install_backend(monkeypatch, backend)
    old_source = setup_dialogue.Dialogue.source

    def changed(app):
        result = old_source(app)
        app.values["PGDATABASE"] = "edited"
        app.dirty = True
        return result

    monkeypatch.setattr(setup_dialogue.Dialogue, "source", changed)
    result = CliRunner().invoke(main, ["--plain", "setup"], input="n\n" + save_response + "\n")
    assert result.exit_code == 0, result.output
    assert backend.writes == []
    text = (tmp_path / ".env").read_text()
    assert ("edited" in text) == (save_response == "y")
    assert "PGPASSWORD" not in text
    assert (
        "Configuration: Saved." if save_response == "y" else "Changes were not saved."
    ) in result.output


def test_save_failure_then_new_path_does_not_repeat_database_actions(tmp_path, monkeypatch):
    from tushare_downloader import setup_dialogue

    configure(tmp_path, monkeypatch, BASE)
    backend = DialogueBackend()
    install_backend(monkeypatch, backend)
    old_source, old_save = setup_dialogue.Dialogue.source, setup_dialogue.save_config
    calls = []

    def changed(app):
        result = old_source(app)
        app.dirty = True
        return result

    def fail_once(path, original, updates):
        calls.append(path)
        if len(calls) == 1:
            raise OSError("SECRET disk failure")
        return old_save(path, original, updates)

    monkeypatch.setattr(setup_dialogue.Dialogue, "source", changed)
    monkeypatch.setattr(setup_dialogue, "save_config", fail_once)
    result = CliRunner().invoke(main, ["--plain", "setup"], input="n\ny\np\nnew.env\ny\n")
    assert result.exit_code == 0, result.output
    assert len(calls) == 2 and backend.writes == []
    assert (tmp_path / ".env").read_text() == BASE
    assert (tmp_path / "new.env").exists()
    assert "SECRET" not in result.output


def test_edited_target_is_used_by_check_apply_and_verify(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch, BASE)
    monkeypatch.setenv("PGHOST", "old_environment_host")

    class Backend(DialogueBackend):
        def __init__(self):
            super().__init__(missing=["daily"])
            self.connections = []

        def inspect(self, settings, *args):
            self.connections.append(("inspect", settings.pg_host))
            if settings.pg_host == "old_environment_host":
                raise RuntimeError("connection unavailable")
            return super().inspect()

        def apply(self, expected, action, settings, *args):
            self.connections.append(("apply", settings.pg_host))
            self.writes.append(action)
            self.state["missing"] = []
            return dict(self.state)

        def verify(self, settings, *args):
            self.connections.append(("verify", settings.pg_host))
            return {"writer": "verified", "reader": "not_checked"}

    backend = Backend()
    install_backend(monkeypatch, backend)
    result = CliRunner().invoke(
        main,
        ["--plain", "setup"],
        input="e\n1\nselected_host\nc\nc\nfixture\nn\nn\n",
    )
    assert result.exit_code == 0, result.output
    assert backend.connections[0] == ("inspect", "old_environment_host")
    assert all(host == "selected_host" for _, host in backend.connections[1:])
    assert ("apply", "selected_host") in backend.connections
    assert ("verify", "selected_host") in backend.connections
    assert "overridden by environment" in result.output
    assert (tmp_path / ".env").read_text() == BASE


@pytest.mark.parametrize("stage", ["inspect", "apply"])
def test_interrupt_keeps_unknown_write_and_stops_later_steps(tmp_path, monkeypatch, stage):
    import json

    configure(tmp_path, monkeypatch, BASE)

    class Interrupted(DialogueBackend):
        def inspect(self, *args):
            if stage == "inspect":
                raise KeyboardInterrupt()
            return super().inspect()

        def apply(self, expected, action, *args):
            self.writes.append(action)
            raise KeyboardInterrupt()

    backend = Interrupted(missing=["daily"])
    install_backend(monkeypatch, backend)
    result = CliRunner().invoke(main, ["--plain", "setup"], input="c\nfixture\n")
    assert result.exit_code == 130, result.output
    assert backend.writes == (["initialize"] if stage == "apply" else [])
    events = [
        json.loads(line)
        for f in (tmp_path / "logs/setup").glob("*.jsonl")
        for line in f.read_text().splitlines()
    ]
    assert events[-1]["exit_code"] == 130
    assert events[-1]["unknown"] == (["initialize"] if stage == "apply" else [])


def test_new_password_mismatch_and_navigation_words_are_literal(tmp_path, monkeypatch):
    import click

    from tushare_downloader.setup_dialogue import Dialogue

    configure(tmp_path, monkeypatch)
    seen = {}

    @click.command()
    @click.pass_context
    def entry(ctx):
        ctx.obj = {"plain": True}
        app = Dialogue(ctx)
        app.password("reader", creation=True)
        seen.update(app.credentials)

    result = CliRunner().invoke(entry, input="wrong\nmismatch\nq\nq\n")
    assert result.exit_code == 0, result.output
    assert "did not match" in result.output
    assert seen == {"reader": {"password": "q"}}
    assert "wrong" not in result.output and "mismatch" not in result.output


@pytest.mark.parametrize("width,plain", [(40, False), (80, True), (120, False)])
def test_output_wraps_and_treats_markup_and_controls_as_text(tmp_path, monkeypatch, width, plain):
    import io
    from types import SimpleNamespace

    from rich.console import Console

    from tushare_downloader.setup_dialogue import Dialogue

    configure(tmp_path, monkeypatch)
    app = Dialogue(SimpleNamespace(obj={"plain": plain}))
    stream = io.StringIO()
    app.console = Console(file=stream, width=width, force_terminal=True)
    value = "[red]literal[/red] /" + "long_path/" * 12 + "\x1b[2J"
    if plain:
        import click

        @click.command()
        def entry():
            app.say(value, "cyan")

        result = CliRunner().invoke(entry)
        text = result.output
        assert "\x1b" not in text
    else:
        app.say(value, "cyan")
        from rich.text import Text

        text = Text.from_ansi(stream.getvalue()).plain
        assert all(len(line) <= width for line in text.splitlines())
    assert "[red]literal[/red]" in text
    assert "long_path/" * 12 in text.replace("\n", "")
    assert "\x1b[2J" not in text


def test_writer_credential_edit_requires_save_decision(tmp_path, monkeypatch):
    import click

    from tushare_downloader.setup_dialogue import Dialogue

    configure(tmp_path, monkeypatch, BASE)
    seen = {}

    @click.command()
    @click.pass_context
    def entry(ctx):
        ctx.obj = {"plain": True}
        app = Dialogue(ctx)
        app.password("writer")
        seen.update(dirty=app.dirty, password=app.credentials["writer"]["password"])

    result = CliRunner().invoke(entry, input="r\nNEW_SECRET\n")
    assert result.exit_code == 0
    assert seen == {"dirty": True, "password": "NEW_SECRET"}
    assert "NEW_SECRET" not in result.output


def test_prompt_default_cannot_emit_terminal_control_sequences(tmp_path, monkeypatch):
    import click

    from tushare_downloader.setup_dialogue import Dialogue

    configure(tmp_path, monkeypatch)

    @click.command()
    @click.pass_context
    def entry(ctx):
        ctx.obj = {"plain": True}
        Dialogue(ctx).ask("Server host", "host\x1b[2J")

    result = CliRunner().invoke(entry, input="safe-host\n", color=True)
    assert result.exit_code == 0
    assert "\x1b" not in result.output
