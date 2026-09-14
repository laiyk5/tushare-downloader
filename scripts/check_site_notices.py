"""Verify supplier provenance and notices in the built documentation artifact."""

import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
notices = root / "docs/third-party"
site = root / "site/third-party"
supplier = json.loads((notices / "inventory.json").read_text())
dist = importlib.metadata.distribution(supplier["supplier"])
assert dist.version == supplier["version"], "Refresh notices after upgrading Zensical"
records = supplier["notices"]
for record in records:
    installed = Path(dist.locate_file(record["supplier_path"]))
    assert hashlib.sha256(installed.read_bytes()).hexdigest() == record["sha256"]

packages = json.loads((notices / "javascript-inventory.json").read_text())
declared = set(
    re.findall(r"Package: ([^@\s]+)@([^\s]+)", (notices / "javascript-NOTICES.txt").read_text())
)
assert declared == {(p["package"], p["version"]) for p in packages}
for package in packages:
    records += package["notices"]
for record in records:
    for directory in (notices, site):
        data = (directory / record["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == record["sha256"], record["file"]
assert (root / "site/assets/javascripts/LICENSE").read_bytes() == (
    notices / "javascript-NOTICES.txt"
).read_bytes()
assert (site / "index.html").is_file()
print(f"Verified {len(records)} supplier notices in source and built site.")
