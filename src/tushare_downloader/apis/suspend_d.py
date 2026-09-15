"""Explicit raw field contract for suspend_d."""

from . import ApiSpec, Field

SUSPEND_D = ApiSpec(
    name="suspend_d",
    fields=(
        Field("ts_code", "text", False),
        Field("trade_date", "date", False),
        Field("suspend_timing", "text"),
        Field("suspend_type", "text"),
    ),
    unique_key=("ts_code", "trade_date"),
    change_kind="append-only",
    query_kind="time-range",
    parameter_names=frozenset({"trade_date", "start_date", "end_date", "ts_code"}),
    row_limit=None,
    stale_scope_verified=True,
    trading_day_filter=True,
)
