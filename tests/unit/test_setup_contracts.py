import pytest

from tushare_downloader.setup_config import read_config, save_config
from tushare_downloader.setup_db import build_plan


def test_preserve_configuration_and_atomic_update(tmp_path):
    path = tmp_path / ".env"
    old = '# Header\nPGHOST=old # server\nCUSTOM="keep"\nDATABASE_URL=ignored\n'
    path.write_text(old)
    original, values = read_config(path)
    assert values["PGHOST"] == "old"
    save_config(path, original, {"PGHOST": "new", "PGPASSWORD": "s'e#c\\ret"})
    new = path.read_text()
    assert "# Header" in new and "# server" in new and 'CUSTOM="keep"' in new
    assert "DATABASE_URL=ignored" in new
    assert read_config(path)[1]["PGPASSWORD"] == "s'e#c\\ret"
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("content", ["PGHOST=a\nPGHOST=b\n", 'PGHOST="a\nb"\n'])
def test_ambiguous_connection_file_is_rejected(tmp_path, content):
    path = tmp_path / ".env"
    path.write_text(content)
    with pytest.raises(ValueError):
        read_config(path)
    assert path.read_text() == content


def test_concurrent_file_edit_is_not_overwritten(tmp_path):
    path = tmp_path / ".env"
    path.write_text("PGHOST=one\n")
    original, _ = read_config(path)
    path.write_text("PGHOST=external\n")
    with pytest.raises(ValueError):
        save_config(path, original, {"PGHOST": "three"})
    assert path.read_text() == "PGHOST=external\n"


def test_symlink_refused(tmp_path):
    target = tmp_path / "target"
    target.write_text("PGHOST=x\n")
    link = tmp_path / ".env"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        read_config(link)


def state(kind="managed", **kw):
    return dict(
        kind=kind,
        writer_exists=True,
        reader_exists=True,
        roles_safe=True,
        missing=[],
        grants_needed=False,
        **kw,
    )


def test_managed_database_no_change():
    assert build_plan(state()) == []


@pytest.mark.parametrize("kind", ["external", "incompatible", "foreign-empty"])
def test_unmanaged_database_blocked(kind):
    with pytest.raises(ValueError):
        build_plan(state(kind))


def test_new_database_plan_orders_actors():
    value = state("missing")
    value.update(writer_exists=False, reader_exists=False, grants_needed=True)
    assert build_plan(value) == [
        "create-writer",
        "create-reader",
        "create-database",
        "initialize",
        "grants",
    ]


def test_only_confirmable_grants_required():
    value = state()
    value["grants_needed"] = True
    assert build_plan(value) == ["grants"]


def test_unsafe_role_blocked_even_with_compatible_tables():
    value = state()
    value["roles_safe"] = False
    with pytest.raises(ValueError):
        build_plan(value)
