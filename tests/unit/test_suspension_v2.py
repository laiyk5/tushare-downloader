"""Event contract expectations derived from the revision 5 incident."""

from datetime import date

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.client import RequestError, parse_rows
from tushare_downloader.contracts import contract


def payload(items):
    return {"fields": ["ts_code", "trade_date", "suspend_timing", "suspend_type"], "items": items}


@pytest.mark.parametrize("day", ["20260112", "20260113", "20260115", "20260122", "20260320"])
def test_stop_and_resume_same_day_are_distinct_events(day):
    api = get_api("suspend_d")
    items = [["TEST.SH", day, None, "S"], ["TEST.SH", day, None, "R"]]
    rows, received, duplicates = parse_rows(payload(items + [items[0]]), api)
    assert rows == (
        ("TEST.SH", date(int(day[:4]), int(day[4:6]), int(day[6:])), None, "S"),
        ("TEST.SH", date(int(day[:4]), int(day[4:6]), int(day[6:])), None, "R"),
    )
    assert (received, duplicates) == (3, 1)


def test_same_event_conflicting_timing_remains_an_error():
    with pytest.raises(RequestError, match="same key"):
        parse_rows(
            payload(
                [["TEST.SH", "20260112", None, "S"], ["TEST.SH", "20260112", "10:00-10:10", "S"]]
            ),
            get_api("suspend_d"),
        )


@pytest.mark.parametrize("kind", [None, "", " \t"])
def test_event_type_cannot_be_empty(kind):
    with pytest.raises(RequestError):
        parse_rows(payload([["TEST.SH", "20260112", None, kind]]), get_api("suspend_d"))


def test_event_contract_is_versioned_and_unknown_type_preserved():
    api = get_api("suspend_d")
    assert api.spec_version == "2"
    assert contract(api)["version"] == "2.0.0"
    assert contract(api)["key"] == ("ts_code", "trade_date", "suspend_type")
    assert parse_rows(payload([["TEST.SH", "20260112", None, " X "]]), api)[0][0][-1] == " X "
