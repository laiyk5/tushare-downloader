# APIs and tables

| API/table | Policy | Unique key | Requests |
| --- | --- | --- | --- |
| daily_basic / raw.daily_basic | Normally append-only | ts_code, trade_date | One date per block |
| stock_basic / raw.stock_basic | Mutable snapshot | ts_code | Required statuses L, D, P, G, UN |

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
