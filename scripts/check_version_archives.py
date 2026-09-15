"""Verify migration hashes, legacy assets and local generated HTML links."""

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

r = Path(__file__).resolve().parents[1]
m = json.loads((r / "docs/development/releases/legacy-paths.json").read_text())
for e in m["files"]:
    p = r / e["new_source"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == e["new_sha256"], p
    assert not (r / e["old_source"]).exists()
for a in m["aliases"]:
    old = r / "site" / a["old"]
    new = r / "site" / a["new"]
    assert old.is_file() and new.is_file()
    if a["kind"] == "asset":
        assert old.read_bytes() == new.read_bytes()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.links.append(v)


broken = []
checked = 0
for p in (r / "site").rglob("*.html"):
    parser = Links()
    parser.feed(p.read_text())
    for value in parser.links:
        u = urlsplit(value)
        if u.scheme or u.netloc or not u.path or u.path.startswith("/"):
            continue
        path = (p.parent / unquote(u.path)).resolve()
        if path.is_dir():
            path = path / "index.html"
        if not path.exists():
            broken.append((str(p.relative_to(r / "site")), value))
        checked += 1
print(
    json.dumps(
        {
            "manifest_files": len(m["files"]),
            "aliases": len(m["aliases"]),
            "relative_links_checked": checked,
            "broken": broken,
        },
        ensure_ascii=False,
    )
)
assert not broken
