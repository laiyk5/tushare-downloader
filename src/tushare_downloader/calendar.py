"""Optional trading-day optimization; never silently change the selected policy."""

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from .apis import ApiSpec, Field
from .client import RequestError, TushareClient

TRADE_CAL = ApiSpec(
    name="trade_cal",
    fields=(
        Field("exchange", "text", False),
        Field("cal_date", "date", False),
        Field("is_open", "decimal", False),
    ),
    unique_key=("exchange", "cal_date"),
    change_kind="mutable",
    query_kind="time-range",
    parameter_names=frozenset({"exchange", "start_date", "end_date"}),
)


class CalendarError(RuntimeError):
    """Selected policy cannot be executed; user may explicitly bypass it."""


@dataclass
class CalendarResult:
    requested: list = field(default_factory=list)
    filtered: list = field(default_factory=list)
    mode: str = "off"
    bypassed: bool = False
    attempts: int = 0
    sources: list = field(default_factory=list)


def _rows(rows, year):
    result = {}
    for exchange, day, opened in rows:
        if (
            exchange != "SSE"
            or not isinstance(day, date)
            or day.year != year
            or isinstance(opened, bool)
            or opened not in {"0", "1", 0, 1}
        ):
            raise CalendarError("Invalid trading calendar records.")
        if day in result and result[day] != (opened in {"1", 1}):
            raise CalendarError("Conflicting trading calendar dates.")
        result[day] = opened in {"1", 1}
    return result


def _read(path, year, now, max_age):
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(text)
        if (
            data["version"] != 1
            or data["exchange"] != "SSE"
            or data["source"] != "tushare.trade_cal"
        ):
            raise ValueError()
        acquired = datetime.fromisoformat(data["acquired_at"])
        if acquired.utcoffset() is None or acquired > now:
            raise ValueError()
        rows = [("SSE", date.fromisoformat(day), opened) for day, opened in data["days"]]
        parsed = _rows(rows, year)
        if now - acquired > max_age:
            return None
        return acquired, parsed
    except (KeyError, TypeError, ValueError, CalendarError):
        raise CalendarError(
            "Invalid calendar cache. Remove the affected cache or explicitly bypass filtering."
        ) from None


def _write(path, acquired, days):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(
                {
                    "version": 1,
                    "source": "tushare.trade_cal",
                    "exchange": "SSE",
                    "acquired_at": acquired.isoformat(),
                    "days": [
                        [str(day), "1" if opened else "0"] for day, opened in sorted(days.items())
                    ],
                },
                stream,
            )
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def filter_requests(
    api,
    pending,
    settings,
    *,
    ignore=False,
    dry_run=False,
    now=None,
    client_factory=TushareClient,
    on_attempt=None,
):
    result = CalendarResult(mode=settings.calendar_filter, bypassed=ignore)
    if ignore or settings.calendar_filter == "off" or api.name != "daily_basic" or not pending:
        result.requested = list(pending)
        return result
    if settings.calendar_filter == "basic":
        for block, reason in pending:
            (result.filtered if block.requested_start.weekday() >= 5 else result.requested).append(
                (block, reason)
            )
        return result
    now = now or datetime.now(UTC)
    dates = {block.requested_start for block, _ in pending}
    days = {}
    client = None
    try:
        for year in sorted({day.year for day in dates}):
            path = settings.calendar_cache_dir / f"tushare-SSE-{year}.json"
            cached = _read(path, year, now, settings.calendar_max_age)
            if cached is None:
                if dry_run:
                    raise CalendarError(
                        "Plan incomplete: calendar unavailable. Use basic/off or --ignore-calendar explicitly."
                    )
                if client is None:
                    client = client_factory(settings, on_attempt=on_attempt)
                response = client.query(
                    TRADE_CAL,
                    {"exchange": "SSE", "start_date": f"{year}0101", "end_date": f"{year}1231"},
                )
                parsed = _rows(response.rows, year)
                if not {day for day in dates if day.year == year} <= parsed.keys():
                    raise CalendarError("Calendar is missing candidate dates.")
                _write(path, now, parsed)
                acquired = now
            else:
                acquired, parsed = cached
            if not {day for day in dates if day.year == year} <= parsed.keys():
                raise CalendarError("Calendar cache is missing candidate dates.")
            days.update(parsed)
            result.sources.append(
                {
                    "source": "tushare.trade_cal",
                    "exchange": "SSE",
                    "year": year,
                    "acquired_at": acquired.isoformat(),
                }
            )
        for block, reason in pending:
            (result.requested if days[block.requested_start] else result.filtered).append(
                (block, reason)
            )
        return result
    except (OSError, UnicodeError, RequestError) as error:
        raise CalendarError(
            f"Calendar preparation failed ({getattr(error, 'category', type(error).__name__)}). Choose basic/off or --ignore-calendar explicitly."
        ) from None
    finally:
        if client is not None:
            result.attempts = getattr(client, "attempts", 0)
            client.close()
