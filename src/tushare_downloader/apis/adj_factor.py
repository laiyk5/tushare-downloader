"""Explicit raw field contract for adj_factor."""

from . import ApiSpec, Field

ADJ_FACTOR = ApiSpec(
    name="adj_factor",
    fields=(
        Field("ts_code", "text", False),
        Field("trade_date", "date", False),
        Field("adj_factor", "decimal"),
    ),
    unique_key=("ts_code", "trade_date"),
    change_kind="append-only",
    query_kind="time-range",
    parameter_names=frozenset({"trade_date", "start_date", "end_date", "ts_code"}),
    row_limit=None,
    stale_scope_verified=True,
    trading_day_filter=True,
)
