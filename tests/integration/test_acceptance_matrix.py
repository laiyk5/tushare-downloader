"""Command × change kind × query shape acceptance; unsupported full scopes fail explicitly."""

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tushare_downloader.apis import ApiSpec, get_api
from tushare_downloader.client import ApiResult
from tushare_downloader.config import Settings
from tushare_downloader.download import execute
from tushare_downloader.planning import Block

pytestmark = pytest.mark.integration
DAY = date(2024, 1, 2)
STAMP = datetime(2024, 1, 3, tzinfo=UTC)


def make_row(api, key, value):
    values = [None] * len(api.fields)
    values[0] = key
    if api.query_kind == "time-range":
        values[1] = DAY
        values[2] = Decimal(value)
    else:
        values[api.field_names.index("name")] = value
        values[api.field_names.index("list_status")] = "L"
    return tuple(values)


@pytest.mark.parametrize("command", ["fetch", "refresh", "update"])
@pytest.mark.parametrize("change", ["append-only", "mutable"])
@pytest.mark.parametrize("shape", ["time-range", "snapshot"])
def test_command_matrix(db, tmp_path, monkeypatch, command, change, shape):
    db.initialize()
    monkeypatch.setattr(ApiSpec, "available_end", lambda self, now: DAY)
    api = replace(
        get_api("daily_basic" if shape == "time-range" else "stock_basic"), change_kind=change
    )
    block = Block((DAY - api.block_origin).days if shape == "time-range" else 0, DAY, DAY, DAY, DAY)
    if shape == "snapshot":
        block = Block(0, date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1))
    db.merge(api, block, [make_row(api, "old", "1"), make_row(api, "kept", "1")], STAMP)
    db.failed(api, block, STAMP)
    incoming = (make_row(api, "kept", "2"), make_row(api, "new", "3"))

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def query(self, api, params):
            rows = incoming if shape == "time-range" or params["list_status"] == "L" else ()
            return ApiResult(rows, len(rows), 0, 1)

    settings = Settings(
        token="fixture",
        lookback_days=1,
        max_age=__import__("datetime").timedelta(0),
        log_dir=tmp_path / "logs",
        report_dir=tmp_path / "reports",
        progress="off",
    )
    dates = {"start": DAY, "end": DAY} if command != "update" and shape == "time-range" else {}
    if change == "mutable" and shape == "time-range" and command == "update":
        with pytest.raises(ValueError, match="full-source boundary"):
            execute(db, api, command, settings, client_factory=Client, **dates)
        assert db.counts(api) == (2, 0)
        return
    assert execute(db, api, command, settings, client_factory=Client, **dates) == 0
    reconciles = command == "refresh" or (command == "update" and change == "mutable")
    assert db.counts(api) == ((2, 1) if reconciles else (3, 0))
    summary = [
        json.loads(line)
        for p in settings.log_dir.glob("*")
        for line in p.read_text().splitlines()
        if json.loads(line)["event"] == "invocation_finished"
    ][0]
    assert (summary["inserted"], summary["changed"], summary["unchanged"]) == (1, 1, 0)
    assert summary["committed_rows"] == sum(
        summary[k] for k in ("inserted", "changed", "unchanged", "reactivated")
    )
    assert (
        summary["success"]
        + summary["empty"]
        + summary["failed"]
        + summary["unknown"]
        + summary["unattempted"]
        == 1
    )
