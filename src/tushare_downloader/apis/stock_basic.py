"""Stock snapshot metadata. Enumerated status requests are reconciled as one scope."""

from . import ApiSpec, Field

STOCK_STATUSES = ("L", "D", "P", "G", "UN")

STOCK_BASIC = ApiSpec(
    name="stock_basic",
    fields=(
        Field("ts_code", "text", False),
        *(
            Field(name, "text")
            for name in (
                "symbol",
                "name",
                "area",
                "industry",
                "fullname",
                "enname",
                "cnspell",
                "market",
                "exchange",
                "curr_type",
                "list_status",
            )
        ),
        Field("list_date", "date"),
        Field("delist_date", "date"),
        Field("is_hs", "text"),
    ),
    stale_scope_verified=True,
    unique_key=("ts_code",),
    change_kind="mutable",
    query_kind="snapshot",
    parameter_names=frozenset({"list_status"}),
    requests_per_minute=50,
)
