"""daily_basic is append-only for ordinary updates; refresh can correct history."""

from . import ApiSpec, Field

DAILY_BASIC = ApiSpec(
    name="daily_basic",
    fields=(
        Field("ts_code", "text", False),
        Field("trade_date", "date", False),
        *(
            Field(name, "decimal")
            for name in (
                "close",
                "turnover_rate",
                "turnover_rate_f",
                "volume_ratio",
                "pe",
                "pe_ttm",
                "pb",
                "ps",
                "ps_ttm",
                "dv_ratio",
                "dv_ttm",
                "total_share",
                "float_share",
                "free_share",
                "total_mv",
                "circ_mv",
            )
        ),
    ),
    stale_scope_verified=True,
    unique_key=("ts_code", "trade_date"),
    change_kind="append-only",
    query_kind="time-range",
    parameter_names=frozenset({"trade_date", "start_date", "end_date", "ts_code"}),
)
