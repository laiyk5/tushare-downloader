"""DL08: release navigation follows series / patch / document hierarchy."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_release_navigation_groups_every_page_under_its_series_and_patch():
    config = tomllib.loads((ROOT / "zensical.toml").read_text())
    development = next(
        item["Development"] for item in config["project"]["nav"] if "Development" in item
    )
    records = next(item["验证记录"] for item in development if "验证记录" in item)
    series_names = [
        next(iter(item)) for item in records if isinstance(next(iter(item.values())), list)
    ]
    assert series_names == ["v0.4.x", "v0.3.x", "v0.2.x", "v0.1.x"]
    seen = []

    def walk(items, ancestors):
        for item in items:
            label, value = next(iter(item.items()))
            if isinstance(value, list):
                walk(value, [*ancestors, label])
            else:
                assert (ROOT / "docs" / value).is_file()
                seen.append(value)
                match = re.match(r"development/releases/v(\d+\.\d+)/v(\d+\.\d+\.\d+)/", value)
                if match:
                    series, patch = match.groups()
                    assert len(ancestors) == 2
                    assert ancestors[0] == f"v{series}.x"
                    assert ancestors[1] in {f"v{patch}", f"v{patch} candidate"}

    walk(records, [])
    assert len(seen) == len(set(seen))
    for series in ("0.4", "0.3", "0.2", "0.1"):
        assert f"development/releases/v{series}/index.md" in seen
        assert f"development/releases/v{series}/v{series}.0/index.md" in seen
    assert "development/releases/v0.3/v0.3.0/benchmark-v0.3.0.md" in seen
    assert "development/releases/v0.4/v0.4.0/acceptance.md" in seen
