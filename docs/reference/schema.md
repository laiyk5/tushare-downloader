# Dataset schema contracts

Public contracts shipped with the software. These describe expected tables, not a live database inspection.

Read through a separate reader account; see [Read your data](../guide/reading-data.md). Use explicit columns and filter `NOT _is_stale` when appropriate.

## adj_factor

Table: `raw.adj_factor` · Schema: **1.0.0** · Primary key: `ts_code, trade_date`

| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |
| --- | --- | --- | --- | --- | --- |
| `ts_code` | text | False | True | Source | Tushare security code |
| `trade_date` | date | False | True | Source | Trading date |
| `adj_factor` | numeric | True | False | Source | Adjustment factor (ratio) |
| `_is_stale` | boolean | False | False | Managed | Missing from a supported reconciliation; not a listing status |
| `_stale_at` | timestamp with time zone | True | False | Managed | Observation time when marked stale (UTC), otherwise NULL |
| `_last_seen_at` | timestamp with time zone | False | False | Managed | Most recent successful source observation time (UTC) |
| `_updated_at` | timestamp with time zone | False | False | Managed | Time of the last stored source-field or stale-state change (UTC) |

Changes: 1.0.0 documents the existing v0.3.0 table structure; first published contract is targeted for v0.4.0. No table migration.

## daily

Table: `raw.daily` · Schema: **1.0.0** · Primary key: `ts_code, trade_date`

| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |
| --- | --- | --- | --- | --- | --- |
| `ts_code` | text | False | True | Source | Tushare security code |
| `trade_date` | date | False | True | Source | Trading date |
| `open` | numeric | True | False | Source | Opening price (CNY) |
| `high` | numeric | True | False | Source | Highest price (CNY) |
| `low` | numeric | True | False | Source | Lowest price (CNY) |
| `close` | numeric | True | False | Source | Closing price (CNY) |
| `pre_close` | numeric | True | False | Source | Previous closing price (CNY) |
| `change` | numeric | True | False | Source | Price change (CNY) |
| `pct_chg` | numeric | True | False | Source | Price change (%) |
| `vol` | numeric | True | False | Source | Trading volume (lots of 100 shares) |
| `amount` | numeric | True | False | Source | Turnover amount (thousand CNY) |
| `_is_stale` | boolean | False | False | Managed | Missing from a supported reconciliation; not a listing status |
| `_stale_at` | timestamp with time zone | True | False | Managed | Observation time when marked stale (UTC), otherwise NULL |
| `_last_seen_at` | timestamp with time zone | False | False | Managed | Most recent successful source observation time (UTC) |
| `_updated_at` | timestamp with time zone | False | False | Managed | Time of the last stored source-field or stale-state change (UTC) |

Changes: 1.0.0 documents the existing v0.3.0 table structure; first published contract is targeted for v0.4.0. No table migration.

## daily_basic

Table: `raw.daily_basic` · Schema: **1.0.0** · Primary key: `ts_code, trade_date`

| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |
| --- | --- | --- | --- | --- | --- |
| `ts_code` | text | False | True | Source | Tushare security code |
| `trade_date` | date | False | True | Source | Trading date |
| `close` | numeric | True | False | Source | Closing price (CNY) |
| `turnover_rate` | numeric | True | False | Source | Turnover rate (%) |
| `turnover_rate_f` | numeric | True | False | Source | Free-float turnover rate (%) |
| `volume_ratio` | numeric | True | False | Source | Volume ratio |
| `pe` | numeric | True | False | Source | Price / earnings ratio |
| `pe_ttm` | numeric | True | False | Source | Price / trailing earnings ratio |
| `pb` | numeric | True | False | Source | Price / book ratio |
| `ps` | numeric | True | False | Source | Price / sales ratio |
| `ps_ttm` | numeric | True | False | Source | Price / trailing sales ratio |
| `dv_ratio` | numeric | True | False | Source | Dividend yield (%) |
| `dv_ttm` | numeric | True | False | Source | Trailing dividend yield (%) |
| `total_share` | numeric | True | False | Source | Total shares (10,000 shares) |
| `float_share` | numeric | True | False | Source | Circulating shares (10,000 shares) |
| `free_share` | numeric | True | False | Source | Free-float shares (10,000 shares) |
| `total_mv` | numeric | True | False | Source | Total market capitalization (10,000 CNY) |
| `circ_mv` | numeric | True | False | Source | Circulating market capitalization (10,000 CNY) |
| `_is_stale` | boolean | False | False | Managed | Missing from a supported reconciliation; not a listing status |
| `_stale_at` | timestamp with time zone | True | False | Managed | Observation time when marked stale (UTC), otherwise NULL |
| `_last_seen_at` | timestamp with time zone | False | False | Managed | Most recent successful source observation time (UTC) |
| `_updated_at` | timestamp with time zone | False | False | Managed | Time of the last stored source-field or stale-state change (UTC) |

Changes: 1.0.0 documents the existing v0.3.0 table structure; first published contract is targeted for v0.4.0. No table migration.

## stk_limit

Table: `raw.stk_limit` · Schema: **1.0.0** · Primary key: `ts_code, trade_date`

| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |
| --- | --- | --- | --- | --- | --- |
| `ts_code` | text | False | True | Source | Tushare security code |
| `trade_date` | date | False | True | Source | Trading date |
| `pre_close` | numeric | True | False | Source | Previous closing price (CNY) |
| `up_limit` | numeric | True | False | Source | Upper price limit (CNY) |
| `down_limit` | numeric | True | False | Source | Lower price limit (CNY) |
| `_is_stale` | boolean | False | False | Managed | Missing from a supported reconciliation; not a listing status |
| `_stale_at` | timestamp with time zone | True | False | Managed | Observation time when marked stale (UTC), otherwise NULL |
| `_last_seen_at` | timestamp with time zone | False | False | Managed | Most recent successful source observation time (UTC) |
| `_updated_at` | timestamp with time zone | False | False | Managed | Time of the last stored source-field or stale-state change (UTC) |

Changes: 1.0.0 documents the existing v0.3.0 table structure; first published contract is targeted for v0.4.0. No table migration.

## stock_basic

Table: `raw.stock_basic` · Schema: **1.0.0** · Primary key: `ts_code`

| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |
| --- | --- | --- | --- | --- | --- |
| `ts_code` | text | False | True | Source | Tushare security code |
| `symbol` | text | True | False | Source | Exchange security symbol |
| `name` | text | True | False | Source | Security short name |
| `area` | text | True | False | Source | Region |
| `industry` | text | True | False | Source | Industry |
| `fullname` | text | True | False | Source | Company full name |
| `enname` | text | True | False | Source | English company name |
| `cnspell` | text | True | False | Source | Chinese abbreviation spelling |
| `market` | text | True | False | Source | Market board |
| `exchange` | text | True | False | Source | Exchange |
| `curr_type` | text | True | False | Source | Trading currency |
| `list_status` | text | True | False | Source | Source listing status (not downloader stale status) |
| `list_date` | date | True | False | Source | Listing date |
| `delist_date` | date | True | False | Source | Delisting date |
| `is_hs` | text | True | False | Source | Stock Connect eligibility code |
| `_is_stale` | boolean | False | False | Managed | Missing from a supported reconciliation; not a listing status |
| `_stale_at` | timestamp with time zone | True | False | Managed | Observation time when marked stale (UTC), otherwise NULL |
| `_last_seen_at` | timestamp with time zone | False | False | Managed | Most recent successful source observation time (UTC) |
| `_updated_at` | timestamp with time zone | False | False | Managed | Time of the last stored source-field or stale-state change (UTC) |

Changes: 1.0.0 documents the existing v0.3.0 table structure; first published contract is targeted for v0.4.0. No table migration.

## suspend_d

Table: `raw.suspend_d` · Schema: **2.0.0** · Primary key: `ts_code, trade_date, suspend_type`

| Field | PostgreSQL type | Nullable | Key | Origin | Meaning / unit |
| --- | --- | --- | --- | --- | --- |
| `ts_code` | text | False | True | Source | Tushare security code |
| `trade_date` | date | False | True | Source | Trading date |
| `suspend_timing` | text | True | False | Source | Suspension time interval |
| `suspend_type` | text | False | True | Source | Event type: S suspension, R resumption |
| `_is_stale` | boolean | False | False | Managed | Missing from a supported reconciliation; not a listing status |
| `_stale_at` | timestamp with time zone | True | False | Managed | Observation time when marked stale (UTC), otherwise NULL |
| `_last_seen_at` | timestamp with time zone | False | False | Managed | Most recent successful source observation time (UTC) |
| `_updated_at` | timestamp with time zone | False | False | Managed | Time of the last stored source-field or stale-state change (UTC) |

Changes: 2.0.0 adds suspend_type to the primary key and requires a nonblank type. Spec 1 / schema 1.0.0 requires explicit migration; see [Upgrade suspend_d](../guide/migrate-suspend-d.md).

Dataset schema versions are independent of software versions. A version identifies structure and semantics, not immutable data. Internal `meta` tables are not a public research interface. Source corrections do not change the schema version.
