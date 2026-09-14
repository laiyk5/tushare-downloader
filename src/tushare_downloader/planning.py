"""Pure fixed-block planning. No stored execution state or I/O."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from .apis import ApiSpec

Command = Literal["fetch", "refresh", "update"]


@dataclass(frozen=True)
class Block:
    id: int
    start: date
    end: date
    requested_start: date
    requested_end: date


@dataclass(frozen=True)
class Observation:
    spec_version: str
    requested_start: date
    requested_end: date
    last_success_at: datetime | None
    last_reconciled_at: datetime | None = None
    empty: bool = False
    failed: bool = False
    local_consistent: bool = True


def block_id(day: date, origin: date, size: int) -> int:
    if size < 1:
        raise ValueError("Block size must be positive")
    return (day - origin).days // size


def blocks(
    start: date,
    end: date,
    *,
    origin: date,
    size: int,
    available_start: date,
    available_end: date,
) -> tuple[Block, ...]:
    """Clip availability, not user range: neighbors inside selected blocks are retained."""
    if size < 1:
        raise ValueError("Block size must be positive")
    if start > end or available_start > available_end:
        raise ValueError("Invalid date range")
    first, last = max(start, available_start), min(end, available_end)
    if first > last:
        return ()
    result = []
    for number in range(block_id(first, origin, size), block_id(last, origin, size) + 1):
        left = origin + timedelta(days=number * size)
        right = left + timedelta(days=size - 1)
        result.append(
            Block(number, left, right, max(left, available_start), min(right, available_end))
        )
    return tuple(result)


def request_reason(
    command: Command,
    block: Block,
    observation: Observation | None,
    *,
    spec_version: str,
    now: datetime,
    max_age: timedelta,
    empty_recheck_age: timedelta,
) -> str | None:
    """Return the reason to request; None means this block can be skipped."""
    if command not in {"fetch", "refresh", "update"}:
        raise ValueError("Unknown command")
    if now.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    if max_age < timedelta(0) or empty_recheck_age <= timedelta(0):
        raise ValueError("Invalid freshness duration")
    if command == "update":
        return "update"
    if command == "refresh" and max_age == timedelta(0):
        return "forced"
    if observation is None:
        return "unseen"
    if observation.spec_version != spec_version:
        return "spec_changed"
    if observation.failed or not observation.local_consistent:
        return "failed_or_inconsistent"
    if (
        observation.requested_start > block.requested_start
        or observation.requested_end < block.requested_end
    ):
        return "range_expanded"
    success = observation.last_success_at
    reconciled = observation.last_reconciled_at
    for timestamp in (success, reconciled):
        if timestamp is not None and (timestamp.utcoffset() is None or timestamp > now):
            return "invalid_timestamp"
    if success is None:
        return "unseen"
    if observation.empty:
        return "empty_due" if now - success >= empty_recheck_age else None
    if command == "fetch":
        return None
    if reconciled is None:
        return "not_reconciled"
    return "expired" if now - reconciled > max_age else None


def update_range(
    spec: ApiSpec, latest: date | None, lookback_days: int, now: datetime
) -> tuple[date, date] | None:
    """Only append-only time data has a lookback window; snapshots bypass date math."""
    if lookback_days < 1:
        raise ValueError("Lookback must be positive")
    if spec.query_kind == "snapshot":
        return None
    if spec.change_kind != "append-only":
        raise ValueError("Mutable update requires an explicit full-source boundary, not lookback")
    if latest is None:
        raise ValueError("No local dated data. Use fetch to initialize a range first.")
    end = spec.available_end(now)
    if latest > end:
        # A user may have fetched today's provisional data. Recheck the published window.
        latest = end
    return latest - timedelta(days=lookback_days - 1), end
