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

    with pytest.raises(RequestError, match="上市状态"):
        retrieve(Client(), api, block, 100000)
