from datetime import UTC, date, datetime

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.client import ApiResult, RequestError
from tushare_downloader.download import retrieve
from tushare_downloader.planning import Block

pytestmark = pytest.mark.integration


def test_snapshot_statuses_merge_stale_and_reappear(db):
    api = get_api("stock_basic")
    db.initialize()
    day = date(2024, 1, 2)
    block = Block(0, day, day, day, day)
    stamp = datetime(2024, 1, 3, tzinfo=UTC)

    def row(key, status):
        values = [key, *[None for _ in api.fields[1:]]]
        values[api.field_names.index("list_status")] = status
        return tuple(values)

    old = row("old.SZ", "L")
    db.merge(api, block, [old], stamp)

    class Client:
        calls = []

        def query(self, api, params):
            self.calls.append(params["list_status"])
            rows = (row("new.SZ", "L"),) if params["list_status"] == "L" else ()
            return ApiResult(rows, len(rows), 0, 1)

    client = Client()
    result = retrieve(client, api, block, 100000)
    assert client.calls == ["L", "D", "P", "G", "UN"]
    counts = db.merge(api, block, result.rows, stamp, reconcile=True)
    assert (counts.inserted, counts.stale) == (1, 1)
    assert db.merge(api, block, [old], stamp).reactivated == 1


def test_mismatched_status_rejected(db):
    api = get_api("stock_basic")
    day = date(2024, 1, 2)
    block = Block(0, day, day, day, day)

    class Client:
        def query(self, *args):
            return ApiResult((("001.SZ", *[None for _ in api.fields[1:]]),), 1, 0, 1)

    with pytest.raises(RequestError, match="listing status"):
        retrieve(Client(), api, block, 100000)


@pytest.mark.parametrize(
    "fault,category",
    [("scope", "scope"), ("budget", "response_size"), ("conflict", "duplicate_conflict")],
)
def test_snapshot_validation_failure_is_recorded_on_its_subrequest(fault, category):
    api = get_api("stock_basic")
    day = date(2024, 1, 2)
    events, calls = [], []

    class Client:
        def query(self, api, params):
            status = params["list_status"]
            calls.append(status)
            values = ["001.SZ", *[None for _ in api.fields[1:]]]
            values[api.field_names.index("list_status")] = "D" if fault == "scope" else status
            return ApiResult((tuple(values),), 1, 0, 1)

    with pytest.raises(RequestError) as error:
        retrieve(
            Client(),
            api,
            Block(0, day, day, day, day),
            1 if fault == "budget" else 100000,
            on_subrequest=lambda *values: events.append(values),
        )
    assert error.value.category == category
    assert calls == (["L", "D"] if fault == "conflict" else ["L"])
    assert events[-1] == (calls[-1], "Failed", 1)
    if fault == "conflict":
        assert events[0] == ("L", "Received", 1)
