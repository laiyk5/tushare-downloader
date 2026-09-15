# APIs and tables

| API/table | Policy | Unique key | Requests |
| --- | --- | --- | --- |
| daily_basic / raw.daily_basic | Normally append-only | ts_code, trade_date | One date per block |
| stock_basic / raw.stock_basic | Mutable snapshot | ts_code | Required statuses L, D, P, G, UN |
| daily / raw.daily | Normally append-only | ts_code, trade_date | One date per block |
| adj_factor / raw.adj_factor | Normally append-only | ts_code, trade_date | One date per block |
| stk_limit / raw.stk_limit | Normally append-only | ts_code, trade_date | One date per block |
| suspend_d / raw.suspend_d | Normally append-only | ts_code, trade_date | One date per block |

Text preserves leading zeros, dates use PostgreSQL date and numbers use Decimal/numeric. Source null becomes SQL NULL. Field order may vary; missing/duplicate fields, invalid types and incorrect row widths fail explicitly.

Daily update ends at yesterday in Asia/Shanghai; historical corrections use refresh. Snapshot reconciliation requires every status request to succeed and the combined result to be nonempty. An empty combined response keeps old rows. Only declared reconciliation scopes may mark missing keys stale.

## Technical columns

| Column | Meaning |
| --- | --- |
| _is_stale | Not returned in the latest successful nonempty reconciliation of its scope |
| _stale_at | Time first marked stale; cleared on reactivation |
| _last_seen_at | Latest successfully committed observation |
| _updated_at | Latest change to source fields or stale state |

Downstream queries usually filter `NOT _is_stale`. Stale rows retain keys and values; reappearing rows reactivate. `meta.schema_info` stores managed versions and database identity; `meta.slices` stores block check facts, not a task queue. Do not edit metadata to change skipping; use refresh.

There is no automatic arbitrary-API schema creation or unrestricted parameter forwarding. See [download policies](../guide/downloading.md).

## Source fields

### daily_basic

| Field | PostgreSQL type | Key member | Nullable |
| --- | --- | --- | --- |
| ts_code | text | Yes | No |
| trade_date | date | Yes | No |
| close | numeric | No | Yes |
| turnover_rate | numeric | No | Yes |
| turnover_rate_f | numeric | No | Yes |
| volume_ratio | numeric | No | Yes |
| pe | numeric | No | Yes |
| pe_ttm | numeric | No | Yes |
| pb | numeric | No | Yes |
| ps | numeric | No | Yes |
| ps_ttm | numeric | No | Yes |
| dv_ratio | numeric | No | Yes |
| dv_ttm | numeric | No | Yes |
| total_share | numeric | No | Yes |
| float_share | numeric | No | Yes |
| free_share | numeric | No | Yes |
| total_mv | numeric | No | Yes |
| circ_mv | numeric | No | Yes |

### stock_basic

| Field | PostgreSQL type | Key member | Nullable |
| --- | --- | --- | --- |
| ts_code | text | Yes | No |
| symbol | text | No | Yes |
| name | text | No | Yes |
| area | text | No | Yes |
| industry | text | No | Yes |
| fullname | text | No | Yes |
| enname | text | No | Yes |
| cnspell | text | No | Yes |
| market | text | No | Yes |
| exchange | text | No | Yes |
| curr_type | text | No | Yes |
| list_status | text | No | Yes |
| list_date | date | No | Yes |
| delist_date | date | No | Yes |
| is_hs | text | No | Yes |

### daily

| Field | PostgreSQL type | Key member | Nullable |
| --- | --- | --- | --- |
| ts_code | text | Yes | No |
| trade_date | date | Yes | No |
| open | numeric | No | Yes |
| high | numeric | No | Yes |
| low | numeric | No | Yes |
| close | numeric | No | Yes |
| pre_close | numeric | No | Yes |
| change | numeric | No | Yes |
| pct_chg | numeric | No | Yes |
| vol | numeric | No | Yes |
| amount | numeric | No | Yes |

### adj_factor

| Field | PostgreSQL type | Key member | Nullable |
| --- | --- | --- | --- |
| ts_code | text | Yes | No |
| trade_date | date | Yes | No |
| adj_factor | numeric | No | Yes |

### stk_limit

| Field | PostgreSQL type | Key member | Nullable |
| --- | --- | --- | --- |
| ts_code | text | Yes | No |
| trade_date | date | Yes | No |
| pre_close | numeric | No | Yes |
| up_limit | numeric | No | Yes |
| down_limit | numeric | No | Yes |

### suspend_d

| Field | PostgreSQL type | Key member | Nullable |
| --- | --- | --- | --- |
| ts_code | text | Yes | No |
| trade_date | date | Yes | No |
| suspend_timing | text | No | Yes |
| suspend_type | text | No | Yes |

## Daily data boundaries

The five daily APIs share fetch, refresh and update policies. Trading-day filtering is an optimization; use `--ignore-calendar` to bypass it. Explicit fetch/refresh may include today in Asia/Shanghai; update stops at yesterday.

`daily` preserves unadjusted prices; volume is in lots and amount in thousands of CNY. `adj_factor` stores raw factors, not adjusted prices. Research code is responsible for interpretation and joins. The downloader preserves the returned security universe rather than filtering against the current stock list.

For `suspend_d`, `(ts_code, trade_date)` is a checked working key. Identical duplicates are collapsed; conflicting rows within one daily response fail that block without writing it. Corrections across separate responses update the stored row. An empty response may indicate no suspension/resumption records, but does not prove their absence and does not mark old rows stale.

`refresh` marks missing keys stale only within successfully returned, nonempty daily scopes. Fetch and ordinary append-only updates retain missing keys. Failed, filtered and empty dates cannot clear old rows.

After upgrading, run `tushare-downloader init-db` to add registered tables in a transaction. Existing data and database identity are retained; unregistered pre-existing tables are never taken over.

Official contracts: [daily](https://tushare.pro/document/2?doc_id=27), [adj_factor](https://tushare.pro/document/2?doc_id=28), [stk_limit](https://tushare.pro/document/2?doc_id=183), [suspend_d](https://tushare.pro/document/2?doc_id=214). Permissions and limits depend on the API and account; unavailable access fails explicitly.
