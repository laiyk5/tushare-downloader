"""Explicit raw field contract for stk_limit."""

from . import ApiSpec, Field

STK_LIMIT = ApiSpec(
    name="stk_limit",
    fields=(
        Field("ts_code", "text", False),
        Field("trade_date", "date", False),
        Field("pre_close", "decimal"),
        Field("up_limit", "decimal"),
        Field("down_limit", "decimal"),
    ),
    unique_key=("ts_code", "trade_date"),
    change_kind="append-only",
    query_kind="time-range",
    parameter_names=frozenset({"trade_date", "start_date", "end_date", "ts_code"}),
    row_limit=5800,
    stale_scope_verified=True,
    trading_day_filter=True,
)
