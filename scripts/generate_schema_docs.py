"""Generate or check the public contract reference from shipped definitions."""

import argparse
from pathlib import Path

from tushare_downloader.contracts import markdown

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
path = Path(__file__).resolve().parents[1] / "docs/reference/schema.md"
expected = markdown()
if args.check:
    if not path.exists() or path.read_text() != expected:
        raise SystemExit("Schema reference is out of date; regenerate it.")
else:
    path.write_text(expected)
