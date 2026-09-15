# Read your downloaded data

Connect to PostgreSQL with a read-only account and query the tables in `raw`. You do not need a Tushare token to read data already downloaded. Reading the database does not start a download or consume Tushare API quota.

## 1. Connect with a reader account

Ask your administrator to set up [read-only access](../operations/database.md#read-only-access) and give you these connection details:

| Setting | Typical value | What to enter |
| --- | --- | --- |
| Host | `localhost` | The PostgreSQL server address reachable from your client; Windows, WSL and remote clients may need different addresses |
| Port | `5432` | Your server's configured port |
| Database | `tushare` | The database holding your downloads |
| Username | `tushare_reader` | Your read-only account, not `tushare_writer` |
| Password and TLS | Deployment-specific | Use the authentication and TLS settings supplied by your administrator |

Use these settings in pgAdmin, Excel or your SQL client. In pgAdmin, connect to the database and open **Query Tool** to run the SQL below. Do not share the downloader's writer credentials with downstream clients.

If `psql` is installed, this Bash example connects to a local server and prompts for the password:

```bash
psql -h localhost -p 5432 -U tushare_reader -d tushare -W
```

Replace the host and port when necessary. Client tools do not automatically read the downloader's `.env`; configure each client's connection separately. Keep your existing downloader configuration using its writer account so downloads continue to work. See [Configuration](configuration.md) for downloader settings.

Once connected, confirm the account and database. The following blocks are **SQL**, entered in Query Tool or at the `psql` prompt:

```sql
SELECT current_user, current_database();
```

Expect your reader account and the intended database before continuing.

## 2. Run a small query

Read up to 20 daily price rows from a range you have downloaded:

```sql
SELECT ts_code, trade_date, open, high, low, close
FROM raw.daily
WHERE NOT _is_stale
  AND trade_date BETWEEN DATE '2024-01-02' AND DATE '2024-01-05'
ORDER BY trade_date, ts_code
LIMIT 20;
```

Change the dates to your downloaded range. Both dates are included. To select one stock, add `AND ts_code = '000001.SZ'` before `ORDER BY`.

Use explicit column names and the full table name, such as `raw.daily`. This keeps your query clear and avoids depending on column order or the client's schema search path. Application code should pass filter values as query parameters rather than build SQL from user input.

| Table | Data |
| --- | --- |
| `raw.daily` | Daily prices and trading volume |
| `raw.daily_basic` | Daily valuation and other indicators |
| `raw.adj_factor` | Adjustment factors |
| `raw.stk_limit` | Daily price limits |
| `raw.suspend_d` | Suspension and resumption records |
| `raw.stock_basic` | The downloaded stock information snapshot |

Each API is downloaded separately: data in `daily_basic` does not imply data in `daily`. See [APIs and tables](../reference/apis.md) for supported fields and source documentation. Check units before combining values; prices are not automatically adjusted, and missing values are not automatically filled with zero.

## 3. Understand stale rows

Start ordinary research queries with `WHERE NOT _is_stale`. A stale row is retained locally after a supported reconciliation no longer found its key in the source. It is not automatically deleted.

Non-stale does **not** mean a stock is currently listed or trading. To read currently listed stocks from your downloaded snapshot, apply the business filter explicitly:

```sql
SELECT ts_code, name, list_status, list_date
FROM raw.stock_basic
WHERE NOT _is_stale
  AND list_status = 'L'
ORDER BY ts_code
LIMIT 20;
```

For an investigation, you can deliberately include or select stale rows:

```sql
SELECT ts_code, trade_date, _stale_at
FROM raw.daily
WHERE _is_stale
ORDER BY trade_date DESC, ts_code
LIMIT 20;
```

Refresh and update operations can correct values or reactivate rows. Stale detection depends on the API and download command; absence of stale rows is not proof that the source has never removed data. See [Downloads and reports](downloading.md).

## 4. Check the latest date

```sql
SELECT max(trade_date) AS latest_active_date
FROM raw.daily
WHERE NOT _is_stale;
```

`NULL` means there are no non-stale rows with a data date. A recent maximum date does not prove every earlier date or stock is present. `stock_basic` is a snapshot; its `list_date` is a stock's listing date, not the snapshot's download date.

Exact row counts can scan a large table. Start with a small date range and selected columns instead of downloading the entire table into your client.

## 5. Optional: save a common query as a view

A regular view saves a query under a name. It does not make a second copy of the data and does not need a separate refresh after the underlying rows change.

If you repeatedly use the same columns and stale filter, ask an administrator or your research maintainer to create a view. The reader account should not create or modify it. In an existing, user-managed `analysis` schema, the maintainer can run:

```sql
CREATE VIEW analysis.daily_active
WITH (security_invoker = true) AS
SELECT ts_code, trade_date, open, high, low, close, vol, amount
FROM raw.daily
WHERE NOT _is_stale;

GRANT USAGE ON SCHEMA analysis TO tushare_reader;
GRANT SELECT ON analysis.daily_active TO tushare_reader;
```

The maintainer needs permission to create the view and access its source. If the schema is missing or the view name already exists, ask them to inspect it first; do not replace an existing object blindly. The view uses the caller's underlying table permissions, so the reader still needs access to `raw.daily`.

You can then query it with your reader account:

```sql
SELECT ts_code, trade_date, close
FROM analysis.daily_active
WHERE trade_date = DATE '2024-01-02'
ORDER BY ts_code;
```

These views are optional and user-maintained. The downloader does not create or manage them. A view is not inherently read-only: the reader account's permissions must deny writes to both views and tables. This filter is a convenience, not a security boundary; the reader can still query `raw.daily` directly.

## 6. Know what can change while you read

Independent download blocks commit separately. During a long download, a query may see some blocks updated and others still unchanged. A query does not read uncommitted changes, but separate queries can see different committed states.

For several queries that must observe the same database snapshot, run them in one short transaction using the same client connection:

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;

SELECT max(trade_date) FROM raw.daily WHERE NOT _is_stale;
SELECT max(trade_date) FROM raw.daily_basic WHERE NOT _is_stale;

COMMIT;
```

Finish the transaction promptly; use `ROLLBACK` if you abandon it. This fixes the database snapshot for those queries, not the source publication time of every dataset. Separate Excel queries do not necessarily share this transaction.

Stable table structure does not mean immutable data. Corrections and cleanup can change or remove rows. For reproducible research, keep your own dated data snapshot or export as well as the query and software version. Review the [upgrade guide](../operations/upgrading.md) before changing software versions.

## Common problems

| Symptom | Next step |
| --- | --- |
| Connection refused or timed out | Check that PostgreSQL is running and that the host/port is reachable from this client |
| Password authentication failed | Check the reader credentials and server authentication settings; do not switch to writer as a workaround |
| Permission denied for schema or table | Ask the administrator to check reader grants, including grants for newly added tables |
| Relation does not exist | Check the database and full `raw.<api>` name; ask the downloader operator whether initialization has created that API table |
| Query returns no rows | Check the API, date range and filters against the actual download report; an empty query is not a connection failure |
| Query is slow | Reduce the date range and columns first; ask the administrator to inspect the query plan if needed |

For an Excel walkthrough, continue to [Excel example](excel.md). The same PostgreSQL tables and reader account work with other SQL clients.

## Inspect local state and field contracts

```bash
tushare-downloader schema daily
tushare-downloader inspect daily
tushare-downloader inspect daily --counts
```

`schema` works offline and describes the expected contract shipped with the software.
`inspect` connects using your selected downloader configuration; use `-c reader.env` before the
command for a separate reader configuration, and check environment overrides. It needs read access
to `raw` plus `meta.schema_info` and `meta.slices`. It downloads nothing and creates no report or log.
Exact counts are optional because they can scan a large table. See [field contracts](../reference/schema.md).
