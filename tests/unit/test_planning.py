from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.planning import (
    Block,
    Observation,
    block_id,
    blocks,
    request_reason,
    update_range,
)

ORIGIN = date(2024, 1, 1)
NOW = datetime(2024, 1, 20, tzinfo=UTC)
BLOCK = Block(0, ORIGIN, ORIGIN, ORIGIN, ORIGIN)


@pytest.mark.parametrize("offset,expected", [(-8, -2), (-7, -1), (-1, -1), (0, 0), (6, 0), (7, 1)])
def test_address_boundaries(offset, expected):
    assert block_id(ORIGIN + timedelta(days=offset), ORIGIN, 7) == expected


def test_whole_block_and_availability_clip():
    result = blocks(
        date(2024, 1, 3),
        date(2024, 1, 9),
        origin=ORIGIN,
        size=7,
        available_start=ORIGIN,
        available_end=date(2024, 1, 10),
    )
    assert [(b.id, b.requested_start.day, b.requested_end.day) for b in result] == [
        (0, 1, 7),
        (1, 8, 10),
    ]


def reason(command, observation, **kwargs):
    return request_reason(
        command,
        BLOCK,
        observation,
        spec_version="1",
        now=NOW,
        max_age=kwargs.get("max_age", timedelta(days=1)),
        empty_recheck_age=timedelta(days=1),
    )


@pytest.mark.parametrize("seconds,expected", [(86399, None), (86400, None), (86401, "expired")])
def test_refresh_age_boundary(seconds, expected):
    stamp = NOW - timedelta(seconds=seconds)
    obs = Observation("1", ORIGIN, ORIGIN, stamp, stamp)
    assert reason("refresh", obs) == expected
    assert reason("fetch", obs) is None
    assert reason("update", obs) == "update"


def test_force_refresh():
    assert reason("refresh", None, max_age=timedelta(0)) == "forced"


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"spec_version": "2"}, "spec_changed"),
        ({"failed": True}, "failed_or_inconsistent"),
        ({"local_consistent": False}, "failed_or_inconsistent"),
        ({"requested_start": ORIGIN + timedelta(days=1)}, "range_expanded"),
        ({"last_success_at": NOW + timedelta(seconds=1)}, "invalid_timestamp"),
        ({"last_success_at": None}, "unseen"),
        ({"empty": True, "last_success_at": NOW - timedelta(days=1)}, "empty_due"),
    ],
)
def test_observation_classes(changes, expected):
    assert (
        reason("fetch", replace(Observation("1", ORIGIN, ORIGIN, NOW, NOW), **changes)) == expected
    )


def test_update_uses_latest_date():
    assert update_range(get_api("daily_basic"), date(2024, 1, 10), 7, NOW) == (
        date(2024, 1, 4),
        date(2024, 1, 19),
    )
    assert update_range(get_api("stock_basic"), None, 7, NOW) is None
    with pytest.raises(ValueError):
        update_range(get_api("daily_basic"), None, 7, NOW)


def test_invalid_block_size_even_outside_range():
    with pytest.raises(ValueError):
        blocks(
            ORIGIN,
            ORIGIN,
            origin=ORIGIN,
            size=0,
            available_start=date(2025, 1, 1),
            available_end=date(2025, 1, 2),
        )


@pytest.mark.parametrize(
    "seconds,expected", [(86399, None), (86400, "empty_due"), (86401, "empty_due")]
)
@pytest.mark.parametrize("command", ["fetch", "refresh"])
def test_empty_recheck_boundary_and_force_priority(seconds, expected, command):
    stamp = NOW - timedelta(seconds=seconds)
    obs = Observation("1", ORIGIN, ORIGIN, stamp, stamp, empty=True)
    assert reason(command, obs) == expected
    assert reason("refresh", obs, max_age=timedelta(0)) == "forced"


def test_update_clips_future_latest_before_lookback_at_shanghai_midnight():
    api = get_api("daily_basic")
    before = datetime(2024, 1, 2, 15, 59, 59, tzinfo=UTC)
    after = before + timedelta(seconds=1)
    assert update_range(api, date(2024, 1, 10), 2, before) == (date(2023, 12, 31), date(2024, 1, 1))
    assert update_range(api, date(2024, 1, 10), 2, after) == (date(2024, 1, 1), date(2024, 1, 2))


def test_provisional_success_is_rechecked_after_stable_endpoint():
    from types import SimpleNamespace

    from tushare_downloader.config import Settings
    from tushare_downloader.download import plan

    api = get_api("daily_basic")
    day = date(2024, 1, 2)
    early = datetime(2024, 1, 2, 10, tzinfo=UTC)
    stable = datetime(2024, 1, 3, 0, tzinfo=UTC)
    observation = Observation(api.spec_version, day, day, early, early)
    store = SimpleNamespace(observation=lambda *args: observation)
    selected = plan(store, api, "fetch", Settings(), day, day, now=stable)
    assert selected[0][1] == "failed_or_inconsistent"
    observation = replace(observation, last_success_at=stable, last_reconciled_at=stable)
    assert (
        plan(store, api, "fetch", Settings(), day, day, now=stable + timedelta(seconds=1))[0][1]
        is None
    )
