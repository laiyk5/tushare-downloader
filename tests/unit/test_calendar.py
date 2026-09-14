from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from tushare_downloader.apis import get_api
from tushare_downloader.calendar import CalendarError, _write, filter_requests
from tushare_downloader.config import Settings
from tushare_downloader.planning import blocks

NOW = datetime(2026, 9, 14, tzinfo=UTC)


@pytest.fixture
def setup(tmp_path):
    settings = Settings(calendar_cache_dir=tmp_path / "calendar")
    pending = [
        (b, "missing")
        for b in blocks(
            date(2026, 9, 4),
            date(2026, 9, 7),
            origin=date(1970, 1, 1),
            size=1,
            available_start=date(1900, 1, 1),
            available_end=date(2026, 9, 14),
        )
    ]
    return settings, pending


def test_basic_and_bypass_have_no_external_access(setup):
    settings, pending = setup

    def forbidden(*a, **k):
        raise AssertionError("Unexpected network")

    basic = filter_requests(get_api("daily_basic"), pending, settings, client_factory=forbidden)
    assert [b.requested_start.day for b, _ in basic.requested] == [4, 7]
    assert len(basic.filtered) == 2
    for mode, ignore, api in [
        ("calendar", True, "daily_basic"),
        ("off", False, "daily_basic"),
        ("calendar", False, "stock_basic"),
    ]:
        result = filter_requests(
            get_api(api),
            pending,
            replace(settings, calendar_filter=mode),
            ignore=ignore,
            client_factory=forbidden,
        )
        assert result.requested == pending and not result.filtered
    assert not settings.calendar_cache_dir.exists()


def test_valid_calendar_overrides_weekend_and_cache_age_equal(setup):
    settings, pending = setup
    settings = replace(settings, calendar_filter="calendar")
    days = {b.requested_start: b.requested_start.day == 5 for b, _ in pending}
    _write(settings.calendar_cache_dir / "tushare-SSE-2026.json", NOW - timedelta(days=1), days)
    result = filter_requests(get_api("daily_basic"), pending, settings, now=NOW, dry_run=True)
    assert [b.requested_start.day for b, _ in result.requested] == [5]
    assert result.attempts == 0 and len(result.filtered) == 3


def test_missing_cache_dry_run_does_not_write(setup):
    settings, pending = setup
    with pytest.raises(CalendarError, match="Plan incomplete"):
        filter_requests(
            get_api("daily_basic"),
            pending,
            replace(settings, calendar_filter="calendar"),
            now=NOW,
            dry_run=True,
        )
    assert not settings.calendar_cache_dir.exists()


def test_refresh_missing_then_use_cache(setup):
    settings, pending = setup
    settings = replace(settings, calendar_filter="calendar")
    calls = []

    class Client:
        attempts = 1

        def __init__(self, *a, **k):
            pass

        def query(self, spec, params):
            calls.append((spec.name, params))
            return SimpleNamespace(rows=[("SSE", b.requested_start, "1") for b, _ in pending])

        def close(self):
            pass

    first = filter_requests(
        get_api("daily_basic"), pending, settings, now=NOW, client_factory=Client
    )
    second = filter_requests(
        get_api("daily_basic"), pending, settings, now=NOW, client_factory=Client
    )
    assert len(calls) == 1 and calls[0][1] == {
        "exchange": "SSE",
        "start_date": "20260101",
        "end_date": "20261231",
    }
    assert first.requested == second.requested == pending
    assert first.attempts == 1 and second.attempts == 0


@pytest.mark.parametrize("kind", ["corrupt", "future", "missing-date"])
def test_unusable_cache_never_silently_falls_back(setup, kind):
    settings, pending = setup
    settings = replace(settings, calendar_filter="calendar")
    path = settings.calendar_cache_dir / "tushare-SSE-2026.json"
    days = {b.requested_start: True for b, _ in pending}
    if kind == "missing-date":
        days.pop(next(iter(days)))
    _write(path, NOW + timedelta(seconds=1) if kind == "future" else NOW, days)
    if kind == "corrupt":
        path.write_text("bad json")
    with pytest.raises(CalendarError):
        filter_requests(get_api("daily_basic"), pending, settings, now=NOW, dry_run=True)
    result = filter_requests(get_api("daily_basic"), pending, settings, now=NOW, ignore=True)
    assert result.requested == pending
