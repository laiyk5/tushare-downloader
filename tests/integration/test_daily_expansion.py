"""Real PostgreSQL checks for new contracts and the additive registry upgrade."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tushare_downloader import storage
from tushare_downloader.apis import APIS, get_api
from tushare_downloader.planning import Block
from tushare_downloader.storage import StorageError

pytestmark = pytest.mark.integration
DAY = date(2026, 8, 3)
BLOCK = Block(1, DAY, DAY, DAY, DAY)
STAMP = datetime(2026, 8, 4, tzinfo=UTC)


def row(api, key="000001.SZ", value="1"):
    return (
        key,
        DAY,
        *[
            Decimal(value) if f.kind == "decimal" else None if f.name == "suspend_timing" else "S"
            for f in api.fields[2:]
        ],
    )


@pytest.mark.parametrize("name", ["daily", "adj_factor", "stk_limit", "suspend_d"])
def test_new_api_reconciliation_and_empty_preservation(db, name):
    db.initialize()
    api = get_api(name)
    assert db.merge(api, BLOCK, [row(api), row(api, "000002.SZ")], STAMP).inserted == 2
    assert db.merge(api, BLOCK, [row(api)], STAMP, reconcile=True).stale == 1
    assert db.counts(api) == (1, 1)
    db.merge(api, BLOCK, [], STAMP, reconcile=True)
    assert db.counts(api) == (1, 1)
    assert db.merge(api, BLOCK, [row(api, "000002.SZ")], STAMP).reactivated == 1
    assert db.counts(api) == (2, 0)


def test_additive_upgrade_preserves_identity_rows_and_observation(db, monkeypatch):
    old = {name: APIS[name] for name in ("daily_basic", "stock_basic")}
    monkeypatch.setattr(storage, "APIS", old)
    identity = db.initialize()
    api = get_api("daily_basic")
    db.merge(api, BLOCK, [row(api)], STAMP)
    observed = db.observation(api, BLOCK)
    monkeypatch.setattr(storage, "APIS", APIS)
    assert db.initialize() == identity
    assert db.initialize() == identity
    assert db.observation(api, BLOCK) == observed
    assert db.counts(api) == (1, 0)
    for registered in APIS.values():
        assert db.validate(registered) == identity


def test_additive_upgrade_rolls_back_when_later_table_is_unmanaged(db, monkeypatch):
    monkeypatch.setattr(
        storage, "APIS", {name: APIS[name] for name in ("daily_basic", "stock_basic")}
    )
    identity = db.initialize()
    before = db.identity()
    db.conn.execute("CREATE TABLE raw.suspend_d (unmanaged text)")
    monkeypatch.setattr(storage, "APIS", APIS)
    with pytest.raises(StorageError, match="ownership"):
        db.initialize()
    assert db.identity() == before
    assert db.identity()[0] == identity
    for name in ("daily", "adj_factor", "stk_limit"):
        assert db.conn.execute("SELECT to_regclass(%s)", (f"raw.{name}",)).fetchone()[0] is None
