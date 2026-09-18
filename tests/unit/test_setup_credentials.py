"""H02/H03: private inputs must not change target identity or leak contents."""

import json
import os

import pytest

from tushare_downloader.setup_credentials import load_credentials, writer_password


def private(tmp_path, data):
    path = tmp_path / "credentials.json"
    path.write_text(data)
    path.chmod(0o600)
    return path


@pytest.mark.parametrize(
    "data",
    [
        '{"version":true}',
        '{"version":2}',
        '{"version":1,"writer":null}',
        '{"version":1,"writer":{"password":null}}',
        '{"version":1,"writer":{"password":"SECRET","password":"x"}}',
        '{"version":1,"host":"SECRET"}',
        '{"version":1,"admin":{}}',
        '{"version":1,"reader":{"allow_passwordless_creation":1}}',
        '{"version":1,"writer":{"password":"SECRET","allow_passwordless_creation":true}}',
        '\ufeff{"version":1}',
        "SECRET invalid json",
    ],
)
def test_invalid_inputs_are_safe(tmp_path, data):
    with pytest.raises(ValueError) as error:
        load_credentials(private(tmp_path, data))
    assert "SECRET" not in str(error.value)


def test_size_boundary(tmp_path):
    data = '{"version":1}'
    assert load_credentials(private(tmp_path, data.ljust(65536))) == {"version": 1}
    with pytest.raises(ValueError):
        load_credentials(private(tmp_path, data.ljust(65537)))


def test_permissions_and_symlink(tmp_path):
    path = private(tmp_path, '{"version":1}')
    path.chmod(0o640)
    with pytest.raises(ValueError):
        load_credentials(path)
    path.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(path)
    with pytest.raises(ValueError):
        load_credentials(link)


def test_reader_admin_cannot_override_identity(tmp_path):
    for role in ("writer", "reader"):
        with pytest.raises(ValueError):
            load_credentials(private(tmp_path, json.dumps({"version": 1, role: {"user": "x"}})))
    value = load_credentials(private(tmp_path, '{"version":1,"admin":{"user":"postgres"}}'))
    assert value["admin"]["maintenance_database"] == "postgres"


def test_writer_empty_preserves_existing_and_passwordless_conflict():
    assert writer_password({}, "old") == "old"
    assert writer_password({"writer": {"password": ""}}, "old") == "old"
    assert writer_password({"writer": {"password": "new"}}, "old") == "new"
    with pytest.raises(ValueError):
        writer_password({"writer": {"allow_passwordless_creation": True}}, "old")


def test_nonregular_input_does_not_wait(tmp_path):
    path = tmp_path / "pipe"
    os.mkfifo(path, 0o600)
    with pytest.raises(ValueError):
        load_credentials(path)


@pytest.mark.parametrize(
    "data",
    [
        '{"version":1,"version":1}',
        '{"version":1,"admin":{"user":"postgres","user":"other"}}',
        '{"version":1,"reader":{"password":"SECRET","password":"other"}}',
        '{"version":1,"admin":{"user":"postgres","host":"SECRET"}}',
        '{"version":1,"writer":{"unknown":"SECRET"}}',
        '{"version":1,"reader":{"unknown":"SECRET"}}',
        '{"version":1,"admin":[]}',
        '{"version":1,"writer":[]}',
        '{"version":1,"reader":[]}',
        '{"version":1,"admin":{"user":42}}',
        '{"version":1,"admin":{"user":"postgres","maintenance_database":null}}',
    ],
)
def test_all_credential_levels_reject_duplicates_unknown_keys_and_wrong_types(tmp_path, data):
    path = private(tmp_path, data)
    before = path.read_bytes()
    with pytest.raises(ValueError) as error:
        load_credentials(path)
    assert "SECRET" not in str(error.value)
    assert path.read_bytes() == before


def test_owner_mismatch_is_rejected_before_json_decode(tmp_path, monkeypatch):
    import tushare_downloader.setup_credentials as module

    path = private(tmp_path, '{"version":1}')
    owner = path.stat().st_uid
    monkeypatch.setattr(module.os, "getuid", lambda: owner + 1)

    def forbidden(*args, **kwargs):
        raise AssertionError("Wrong owner must be rejected before parsing")

    monkeypatch.setattr(module.json, "loads", forbidden)
    with pytest.raises(ValueError, match="owned regular file"):
        load_credentials(path)


def test_directory_missing_file_and_private_readonly_file(tmp_path):
    with pytest.raises(ValueError):
        load_credentials(tmp_path)
    with pytest.raises(ValueError):
        load_credentials(tmp_path / "missing")
    path = private(tmp_path, '{"version":1}')
    path.chmod(0o400)
    assert load_credentials(path) == {"version": 1}
    assert path.stat().st_mode & 0o777 == 0o400


def test_invalid_credentials_fail_cli_before_database_session(tmp_path, monkeypatch):
    from click.testing import CliRunner

    from tushare_downloader import setup_headless
    from tushare_downloader.cli import main

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PGHOST", "localhost")
    monkeypatch.setenv("PGDATABASE", "fixture")
    monkeypatch.setenv("PGUSER", "writer")

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid credentials must never create a database session")

    monkeypatch.setattr(setup_headless, "SetupSession", forbidden)
    path = private(tmp_path, '{"version":1,"reader":{"unknown":"SECRET"}}')
    result = CliRunner().invoke(
        main, ["setup", "--headless", "--apply", "--credentials-file", str(path)]
    )
    assert result.exit_code == 2
    assert "SECRET" not in result.output
    assert not (tmp_path / "logs").exists()
