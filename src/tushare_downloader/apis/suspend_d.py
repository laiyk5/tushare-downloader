"""Explicit raw field contract for suspend_d."""

from dataclasses import replace

from . import ApiSpec, Field

SUSPEND_D = ApiSpec(
    name="suspend_d",
    description="Trading suspension and resumption events",
    display_kind="Daily events",
    fields=(
        Field("ts_code", "text", False),
        Field("trade_date", "date", False),
        Field("suspend_timing", "text"),
        Field("suspend_type", "text", False),
    ),
    unique_key=("ts_code", "trade_date", "suspend_type"),
    spec_version="2",
    change_kind="append-only",
    query_kind="time-range",
    parameter_names=frozenset({"trade_date", "start_date", "end_date", "ts_code"}),
    row_limit=None,
    stale_scope_verified=True,
    trading_day_filter=True,
    empty_response_note="Empty response may indicate no suspension/resumption records.",
)

# Explicit historical shape: never interpret spec 1 using the new key.
SUSPEND_D_V1 = replace(
    SUSPEND_D,
    spec_version="1",
    unique_key=("ts_code", "trade_date"),
    fields=SUSPEND_D.fields[:-1] + (Field("suspend_type", "text"),),
)
