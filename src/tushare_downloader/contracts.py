"""Versioned public contracts; identifiers are explicit, never inferred from a version string."""

from .apis import APIS
from .storage import columns

VERSIONS = {
    (1, name, "1"): "1.0.0"
    for name in ("daily", "daily_basic", "stock_basic", "adj_factor", "stk_limit", "suspend_d")
}
VERSIONS[(1, "suspend_d", "2")] = "2.0.0"

DESCRIPTIONS = {
    "ts_code": "Tushare security code",
    "trade_date": "Trading date",
    "open": "Opening price (CNY)",
    "high": "Highest price (CNY)",
    "low": "Lowest price (CNY)",
    "close": "Closing price (CNY)",
    "pre_close": "Previous closing price (CNY)",
    "change": "Price change (CNY)",
    "pct_chg": "Price change (%)",
    "vol": "Trading volume (lots of 100 shares)",
    "amount": "Turnover amount (thousand CNY)",
    "turnover_rate": "Turnover rate (%)",
    "turnover_rate_f": "Free-float turnover rate (%)",
    "volume_ratio": "Volume ratio",
    "pe": "Price / earnings ratio",
    "pe_ttm": "Price / trailing earnings ratio",
    "pb": "Price / book ratio",
    "ps": "Price / sales ratio",
    "ps_ttm": "Price / trailing sales ratio",
    "dv_ratio": "Dividend yield (%)",
    "dv_ttm": "Trailing dividend yield (%)",
    "total_share": "Total shares (10,000 shares)",
    "float_share": "Circulating shares (10,000 shares)",
    "free_share": "Free-float shares (10,000 shares)",
    "total_mv": "Total market capitalization (10,000 CNY)",
    "circ_mv": "Circulating market capitalization (10,000 CNY)",
    "adj_factor": "Adjustment factor (ratio)",
    "up_limit": "Upper price limit (CNY)",
    "down_limit": "Lower price limit (CNY)",
    "suspend_timing": "Suspension time interval",
    "suspend_type": "Event type: S suspension, R resumption",
    "symbol": "Exchange security symbol",
    "name": "Security short name",
    "area": "Region",
    "industry": "Industry",
    "fullname": "Company full name",
    "enname": "English company name",
    "cnspell": "Chinese abbreviation spelling",
    "market": "Market board",
    "exchange": "Exchange",
    "curr_type": "Trading currency",
    "list_status": "Source listing status (not downloader stale status)",
    "list_date": "Listing date",
    "delist_date": "Delisting date",
    "is_hs": "Stock Connect eligibility code",
    "_is_stale": "Missing from a supported reconciliation; not a listing status",
    "_stale_at": "Observation time when marked stale (UTC), otherwise NULL",
    "_last_seen_at": "Most recent successful source observation time (UTC)",
    "_updated_at": "Time of the last stored source-field or stale-state change (UTC)",
}


def contract(api):
    return {
        "api": api.name,
        "table": "raw." + api.name,
        "version": VERSIONS[(1, api.name, api.spec_version)],
        "key": api.unique_key,
        "fields": [
            {
                "name": n,
                "type": t,
                "nullable": not required,
                "key": n in api.unique_key,
                "managed": n.startswith("_"),
                "description": DESCRIPTIONS[n],
            }
            for n, (t, required) in columns(api).items()
        ],
    }


def markdown():
    lines = [
        "# Dataset schema contracts",
        "",
        "Public contracts shipped with the software. "
        "These describe expected tables, not a live database inspection.",
        "",
        "Read through a separate reader account; see [Read your data](../guide/reading-data.md). "
        "Use explicit columns and filter `NOT _is_stale` when appropriate.",
        "",
    ]
    for name in sorted(APIS):
        c = contract(APIS[name])
        lines += [
            f"## {name}",
            "",
            f"Table: `{c['table']}` · Schema: **{c['version']}** · "
            f"Primary key: `{', '.join(c['key'])}`",
            "",
            "| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for f in c["fields"]:
            lines.append(
                f"| `{f['name']}` | {f['type']} | {f['nullable']} | {f['key']} | "
                f"{'Managed' if f['managed'] else 'Source'} | {f['description']} |"
            )
        if name == "suspend_d":
            lines += [
                "",
                "Changes: 2.0.0 adds suspend_type to the primary key and requires a nonblank type. "
                "Spec 1 / schema 1.0.0 requires explicit migration; see [Upgrade suspend_d](../guide/migrate-suspend-d.md).",
                "",
            ]
            continue
        lines += [
            "",
            "Changes: 1.0.0 documents the existing v0.3.0 table structure; "
            "first published contract is targeted for v0.4.0. No table migration.",
            "",
        ]
    lines += [
        "Dataset schema versions are independent of software versions. A version identifies "
        "structure and semantics, not immutable data. Internal `meta` tables are not a public "
        "research interface. Source corrections do not change the schema version.",
        "",
    ]
    return "\n".join(lines)
