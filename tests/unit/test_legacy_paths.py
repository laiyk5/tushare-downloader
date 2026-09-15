import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "legacy", Path(__file__).parents[2] / "scripts/build_legacy_paths.py"
)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def test_aliases_preserve_bytes_and_fragment_fallback(tmp_path):
    new = tmp_path / "new"
    new.mkdir()
    (new / "index.html").write_text("<h1 id='proof'>proof</h1>")
    (new / "data.json").write_bytes(b'{"x":1}\r\n')
    legacy.build_aliases(
        tmp_path,
        [
            {"old": "old/index.html", "new": "new/index.html", "kind": "page"},
            {"old": "old/data.json", "new": "new/data.json", "kind": "asset"},
        ],
    )
    html = (tmp_path / "old/index.html").read_text()
    assert "location.search" in html and "location.hash" in html
    assert 'href="../new/index.html"' in html
    assert (tmp_path / "old/data.json").read_bytes() == (new / "data.json").read_bytes()
    assert not (tmp_path / "search").exists()


@pytest.mark.parametrize("bad", ["../escape", "/absolute", "https://evil.test/a", "a/../../escape"])
def test_unsafe_paths_fail_before_any_output(tmp_path, bad):
    (tmp_path / "target").write_bytes(b"ok")
    entries = [
        {"old": "first", "new": "target", "kind": "asset"},
        {"old": bad, "new": "target", "kind": "asset"},
    ]
    with pytest.raises(ValueError):
        legacy.build_aliases(tmp_path, entries)
    assert not (tmp_path / "first").exists()


def test_missing_duplicate_and_existing_alias_fail(tmp_path):
    (tmp_path / "target").write_bytes(b"ok")
    item = {"old": "old", "new": "target", "kind": "asset"}
    for entries in [[item, item], [{**item, "new": "missing"}]]:
        with pytest.raises(ValueError):
            legacy.build_aliases(tmp_path, entries)
    (tmp_path / "old").write_bytes(b"keep")
    with pytest.raises(ValueError):
        legacy.build_aliases(tmp_path, [item])
    assert (tmp_path / "old").read_bytes() == b"keep"
