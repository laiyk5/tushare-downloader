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
