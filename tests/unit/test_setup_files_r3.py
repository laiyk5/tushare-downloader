"""DBW07/08 and H07: persistence boundaries independent of database setup."""

import json
import stat

import pytest

from tushare_downloader.setup_config import read_config, save_config
from tushare_downloader.setup_events import SetupLog


def test_reader_key_is_editable_but_duplicate_is_rejected(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# Token\nTUSHARE_TOKEN=unchanged\n")
    old, _ = read_config(path)
    save_config(path, old, {"SETUP_READER_USER": "research"})
    assert "# Database access" in path.read_text()
    assert "TUSHARE_TOKEN=unchanged" in path.read_text()
    assert read_config(path)[1]["SETUP_READER_USER"] == "research"
    path.write_text("SETUP_READER_USER=a\nSETUP_READER_USER=b\n")
    with pytest.raises(ValueError):
        read_config(path)


def test_new_file_publish_never_replaces_competitor(tmp_path, monkeypatch):
    import tushare_downloader.setup_config as module

    path = tmp_path / ".env.new"
    original_read = module.read_config

    def competing_read(selected):
        result = original_read(selected)
        if list(tmp_path.glob(".setup-*")):
            path.write_text("competitor\n")
        return result

    monkeypatch.setattr(module, "read_config", competing_read)
    with pytest.raises((ValueError, FileExistsError)):
        save_config(path, None, {"PGHOST": "localhost"})
    assert path.read_text() == "competitor\n"
    assert not list(tmp_path.glob(".setup-*"))


def test_log_replans_have_distinct_step_keys_and_private_mode(tmp_path):
    log = SetupLog(tmp_path, "headless", {"host": "localhost", "password": "SECRET"})
    log.plan(["create_reader"])
    log.emit("step_started", action="create_reader", step_id=1, actor_role="admin")
    log.emit("step_finished", action="create_reader", step_id=1, outcome="failed")
    log.plan(["create_reader"])
    log.emit("step_started", action="create_reader", step_id=1)
    log.emit("step_finished", action="create_reader", step_id=1, outcome="completed")
    log.emit("session_finished", exit_code=0)
    log.close()
    text = log.path.read_text()
    rows = [json.loads(line) for line in text.splitlines()]
    assert "SECRET" not in text
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))
    assert [r["plan_seq"] for r in rows if r["event"] == "step_started"] == [1, 2]
    assert rows[-1]["exit_code"] == 0
    assert stat.S_IMODE(log.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(log.path.parent.stat().st_mode) == 0o700


def test_log_rejects_non_allowlisted_detail(tmp_path):
    log = SetupLog(tmp_path, "tui", {})
    with pytest.raises(ValueError):
        log.emit("config_loaded", password="SECRET")
    log.close()
    assert "SECRET" not in log.path.read_text()


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_failed_file_publish_preserves_original_and_cleans_temporary(
    tmp_path, monkeypatch, operation
):
    import tushare_downloader.setup_config as module

    path = tmp_path / ".env"
    original = b"# Keep\nPGHOST=old\nCUSTOM=unchanged\n"
    path.write_bytes(original)

    def failure(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(module.os, operation, failure)
    with pytest.raises(OSError):
        save_config(path, original, {"PGHOST": "new"})
    assert path.read_bytes() == original
    assert not list(tmp_path.glob(".setup-*"))


def test_edit_during_temporary_write_is_detected_before_replace(tmp_path, monkeypatch):
    import tushare_downloader.setup_config as module

    path = tmp_path / ".env"
    path.write_text("PGHOST=old\n")
    original, _ = read_config(path)
    synchronize = module.os.fsync

    def concurrent_edit(fd):
        synchronize(fd)
        path.write_text("PGHOST=external\n")

    monkeypatch.setattr(module.os, "fsync", concurrent_edit)
    with pytest.raises(ValueError, match="changed before replacement"):
        save_config(path, original, {"PGHOST": "new"})
    assert path.read_text() == "PGHOST=external\n"
    assert not list(tmp_path.glob(".setup-*"))


def test_config_directory_non_utf8_and_unwritable_destination_are_preserved(tmp_path):
    with pytest.raises(ValueError):
        read_config(tmp_path)
    bad = tmp_path / "invalid.env"
    bad.write_bytes(b"PGHOST=\xff\n")
    with pytest.raises(ValueError):
        read_config(bad)
    assert bad.read_bytes() == b"PGHOST=\xff\n"
    folder = tmp_path / "read_only"
    folder.mkdir()
    folder.chmod(0o500)
    try:
        with pytest.raises(PermissionError):
            save_config(folder / ".env", None, {"PGHOST": "new"})
        assert not list(folder.iterdir())
    finally:
        folder.chmod(0o700)


def test_unrelated_update_key_cannot_modify_configuration(tmp_path):
    path = tmp_path / ".env"
    original = b"TUSHARE_TOKEN=keep\n"
    path.write_bytes(original)
    with pytest.raises(ValueError):
        save_config(path, original, {"TUSHARE_TOKEN": "replace"})
    assert path.read_bytes() == original
