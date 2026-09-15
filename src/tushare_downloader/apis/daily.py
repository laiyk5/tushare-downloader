"""Explicit raw field contract for daily."""

from . import ApiSpec, Field

DAILY = ApiSpec(
    name="daily",
    fields=(
        Field("ts_code", "text", False),
        Field("trade_date", "date", False),
        Field("open", "decimal"),
        Field("high", "decimal"),
        Field("low", "decimal"),
        Field("close", "decimal"),
        Field("pre_close", "decimal"),
        Field("change", "decimal"),
        Field("pct_chg", "decimal"),
        Field("vol", "decimal"),
        Field("amount", "decimal"),
    ),
    unique_key=("ts_code", "trade_date"),
    change_kind="append-only",
    query_kind="time-range",
    parameter_names=frozenset({"trade_date", "start_date", "end_date", "ts_code"}),
    row_limit=6000,
    stale_scope_verified=True,
    trading_day_filter=True,
)
