"""Generate old documentation URLs inside a freshly built site; never edit sources."""

import argparse
import html
import json
import posixpath
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


def safe_path(root, value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Invalid compatibility path")
    url = urlsplit(value)
    path = PurePosixPath(value)
    if (
        url.scheme
        or url.netloc
        or url.query
        or url.fragment
        or path.is_absolute()
        or ".." in path.parts
    ):
        raise ValueError("Compatibility paths must stay inside the site")
    resolved = (root / value).resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError("Compatibility path escapes the site")
    return resolved


def build_aliases(site, entries):
    root = Path(site).resolve()
    plans, outputs = [], set()
    for entry in entries:
        source = safe_path(root, entry["new"])
        target = safe_path(root, entry["old"])
        kind = entry["kind"]
        if kind not in {"page", "asset"} or not source.is_file():
            raise ValueError("Invalid kind or missing compatibility destination")
        if target in outputs or target.exists() or target == source:
            raise ValueError("Compatibility output collision")
        outputs.add(target)
        plans.append((source, target, kind))
    # Validate the entire manifest before writing any aliases.
    for source, target, kind in plans:
        if source in outputs or any(
            parent in outputs or (parent.exists() and not parent.is_dir())
            for parent in target.parents
            if parent != root and parent.is_relative_to(root)
        ):
            raise ValueError("Compatibility aliases cannot overlap or form chains")
    for source, target, kind in plans:
        target.parent.mkdir(parents=True, exist_ok=True)
        if kind == "asset":
            target.write_bytes(source.read_bytes())
        else:
            relative = posixpath.relpath(
                source.relative_to(root).as_posix(), target.parent.relative_to(root).as_posix()
            )
            script_url = json.dumps(relative).replace("<", "\\u003c")
            target.write_text(
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="robots" content="noindex"><title>Page moved</title>'
                f'<p>This page has moved. <a href="{html.escape(relative, quote=True)}">Open the current page</a>.</p>'
                "<script>location.replace("
                + script_url
                + " + location.search + location.hash);</script></html>",
                encoding="utf-8",
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument(
        "--manifest", type=Path, default=Path("docs/development/releases/legacy-paths.json")
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    build_aliases(args.site, manifest["aliases"])
    print(f"Built {len(manifest['aliases'])} legacy URL aliases.")


if __name__ == "__main__":
    main()
