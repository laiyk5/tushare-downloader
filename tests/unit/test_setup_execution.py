import time

import click
import pytest
from click.testing import CliRunner

from tushare_downloader.bounded import DeadlineExceeded, bounded
from tushare_downloader.config import Settings
from tushare_downloader.setup_config import read_config, save_config
from tushare_downloader.setup_export import export_bundle
from tushare_downloader.setup_wizard import run_setup, selected_settings


def test_client_deadline_bounds_a_stuck_call():
    start = time.monotonic()
    with pytest.raises(DeadlineExceeded):
        bounded(time.sleep, 10, seconds=0.1)
    assert time.monotonic() - start < 2


def test_fresh_config_with_quoted_password(tmp_path):
    path = tmp_path / "new.env"
    original, _ = read_config(path)
    assert original is None
    save_config(path, original, {"PGUSER": "reader", "PGPASSWORD": 'back\\slash"quote'})
    assert read_config(path)[1]["PGPASSWORD"] == 'back\\slash"quote'


@pytest.mark.parametrize(
    "values",
    [
        {"PGPORT": "0"},
        {"PGPORT": "65536"},
        {"PGSSLMODE": "unknown"},
        {"PGHOST": "a,b"},
        {"INSPECT_TIMEOUT": "6m"},
        {"SETUP_STEP_TIMEOUT": "11m"},
    ],
)
def test_invalid_setup_selection(values):
    with pytest.raises(ValueError):
        selected_settings(values)


def test_unverified_export_is_read_only(tmp_path):
    export_bundle(tmp_path / "bundle", None, Settings(), Settings(), "reader", tmp_path / ".env")
    content = "".join(p.read_text() for p in (tmp_path / "bundle").iterdir())
    assert "Unverified" in content
    assert not any(word in content for word in ["CREATE ROLE", "GRANT ", "CREATE DATABASE"])
    with pytest.raises(ValueError):
        export_bundle(
            tmp_path / "bundle", None, Settings(), Settings(), "reader", tmp_path / ".env"
        )


@click.command()
@click.pass_context
def wizard(ctx):
    ctx.obj = {"env_file": None, "plain": True, "quiet": False}
    run_setup(ctx)


def simulated(monkeypatch, intent, confirm_apply=True, fail_step=False):
    from tushare_downloader import setup_wizard as module

    facts = {
        "kind": "managed",
        "database_id": "fixture",
        "roles_safe": True,
        "writer_exists": True,
        "reader_exists": True,
        "missing": [],
        "grants_needed": intent == 2,
    }
    steps = []

    def fake_bounded(fn, *args, **kwargs):
        if fn.__name__ == "connection_test":
            return ("tushare_writer", "tushare")
        if fn.__name__ == "snapshot":
            return facts.copy()
        if fn.__name__ == "apply_step":
            steps.append(args[1])
            if fail_step:
                raise DeadlineExceeded("deadline")
            facts["grants_needed"] = False
            return facts.copy()
        if fn.__name__ == "verify":
            return {"user": args[0].pg_user}
        raise AssertionError(fn)

    def prompt(label, **kw):
        if label.startswith("Action:"):
            return intent
        if label.startswith("Apply these"):
            return "tushare" if confirm_apply else ""
        return kw.get("default", "")

    def confirm(label, **kw):
        return label == "Use a temporary administrator connection?"

    monkeypatch.setattr(module, "bounded", fake_bounded)
    monkeypatch.setattr(module.click, "prompt", prompt)
    monkeypatch.setattr(module.click, "confirm", confirm)
    return steps


@pytest.mark.parametrize("intent", [1, 2, 3])
def test_setup_modes_without_saving(intent, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    steps = simulated(monkeypatch, intent)
    result = CliRunner().invoke(wizard, [])
    assert result.exit_code == 0, result.output
    assert steps == (["grants"] if intent == 2 else [])
    assert not list(tmp_path.iterdir())


def test_refusing_plan_applies_nothing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    steps = simulated(monkeypatch, 2, confirm_apply=False)
    result = CliRunner().invoke(wizard, [])
    assert result.exit_code == 0 and "Cancelled" in result.output
    assert not steps


def test_unknown_step_does_not_retry_mutation(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    steps = simulated(monkeypatch, 2, fail_step=True)
    result = CliRunner().invoke(wizard, [])
    assert result.exit_code == 1, result.output
    assert steps == ["grants"]
    assert "unknown" in result.output


def test_save_failure_leaves_original(tmp_path, monkeypatch):
    import os

    path = tmp_path / ".env"
    path.write_text("PGHOST=old\n")
    original, _ = read_config(path)

    def fail(*a):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        save_config(path, original, {"PGHOST": "new"})
    assert path.read_text() == "PGHOST=old\n"
    assert list(tmp_path.iterdir()) == [path]


def test_reader_verification_failure_preserves_completed_steps(monkeypatch, tmp_path):
    from tushare_downloader import setup_wizard as module

    monkeypatch.chdir(tmp_path)
    steps = simulated(monkeypatch, 2)
    original = module.bounded

    def fail_reader(fn, *args, **kwargs):
        if fn.__name__ == "verify" and args[0].pg_user == "tushare_reader":
            raise RuntimeError("Authentication failed: no password supplied.")
        return original(fn, *args, **kwargs)

    monkeypatch.setattr(module, "bounded", fail_reader)
    result = CliRunner().invoke(wizard, [])
    assert result.exit_code == 1
    assert "Reader verification failed: tushare_reader" in result.output
    assert "Completed database steps: grants" in result.output
    assert "remain applied" in result.output
    assert "no password supplied" in result.output
    assert "not reset" in result.output
    assert steps == ["grants"]
    assert not list(tmp_path.iterdir())


def test_new_reader_empty_password_requires_explicit_confirmation(monkeypatch, tmp_path):
    from tushare_downloader import setup_wizard as module

    monkeypatch.chdir(tmp_path)
    steps = simulated(monkeypatch, 2)
    original = module.bounded

    def missing_reader(fn, *args, **kwargs):
        result = original(fn, *args, **kwargs)
        if fn.__name__ == "snapshot":
            result["reader_exists"] = False
        return result

    monkeypatch.setattr(module, "bounded", missing_reader)
    result = CliRunner().invoke(wizard, [])
    assert result.exit_code == 0, result.output
    assert "no database changes applied" in result.output
    assert not steps


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "connection failed: fe_sendauth: no password supplied secret=private",
            "no password supplied",
        ),
        ('password authentication failed for user "private"', "password was rejected"),
        ("connection refused: private", "server refused the connection"),
        ("unknown private", "OperationalError"),
    ],
)
def test_worker_connection_errors_are_useful_without_exposing_details(raw, expected):
    import psycopg

    from tushare_downloader.bounded import _call

    class Pipe:
        def send(self, value):
            self.value = value

        def close(self):
            pass

    def fail():
        raise psycopg.OperationalError(raw)

    pipe = Pipe()
    _call(pipe, fail, ())
    assert pipe.value[0] is False
    assert expected in pipe.value[1]
    assert "private" not in pipe.value[1]
