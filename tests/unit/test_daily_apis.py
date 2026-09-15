"""Exercise the actual new contracts through the shared response parser."""

from datetime import date
from decimal import Decimal

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.client import RequestError, parse_rows


@pytest.mark.parametrize("name", ["daily", "adj_factor", "stk_limit", "suspend_d"])
def test_actual_contract_reorders_fields_and_handles_duplicates(name):
    api = get_api(name)
    values = ["000001.SZ", "20260803"] + [
        "1.2500" if f.kind == "decimal" else None for f in api.fields[2:]
    ]
    payload = {"fields": list(reversed(api.field_names)), "items": [values[::-1]] * 2}
    rows, received, duplicates = parse_rows(payload, api)
    assert (received, duplicates) == (2, 1)
    assert rows[0][:2] == ("000001.SZ", date(2026, 8, 3))
    if name != "suspend_d":
        assert rows[0][2] == Decimal("1.2500")
    other = values.copy()
    other[-1] = "R" if name == "suspend_d" else "2"
    payload["items"] = [values[::-1], other[::-1]]
    with pytest.raises(RequestError, match="same key"):
        parse_rows(payload, api)
    assert parse_rows({"fields": list(api.field_names), "items": []}, api) == ((), 0, 0)


def test_suspension_correction_between_responses_is_allowed():
    api = get_api("suspend_d")

    def response(kind):
        return {"fields": list(api.field_names), "items": [["000001.SZ", "20260803", None, kind]]}

    assert parse_rows(response("S"), api)[0] != parse_rows(response("R"), api)[0]


def test_installed_cli_lists_all_registered_contracts():
    from click.testing import CliRunner

    from tushare_downloader.cli import main

    result = CliRunner().invoke(main, ["--plain", "list"])
    assert result.exit_code == 0
    for name in ("daily_basic", "stock_basic", "daily", "adj_factor", "stk_limit", "suspend_d"):
        assert name in result.output
