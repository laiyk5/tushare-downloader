import json
from pathlib import Path

from tushare_downloader.apis import APIS
from tushare_downloader.apis.suspend_d import SUSPEND_D_V1
from tushare_downloader.contracts import contract, markdown


def test_contract_matches_frozen_v03_structure():
    expected = json.loads((Path(__file__).parents[1] / "fixtures/schema-v1.json").read_text())
    assert set(expected) == set(APIS)
    for name, api in APIS.items():
        current = contract(SUSPEND_D_V1 if name == "suspend_d" else api)
        assert current["version"] == "1.0.0"
        assert list(current["key"]) == expected[name]["key"]
        assert {f["name"]: [f["type"], not f["nullable"]] for f in current["fields"]} == expected[
            name
        ]["columns"]
        assert all(f["description"] for f in current["fields"])


def test_generated_reference_is_current():
    assert (Path(__file__).parents[2] / "docs/reference/schema.md").read_text() == markdown()
