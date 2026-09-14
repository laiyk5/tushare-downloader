# Database setup and maintenance

Production database: `tushare`; writer: `tushare_writer`; downstream reader: `tushare_reader`. Tests and benchmarks use separate databases and roles, `tushare_test` and `tushare_bench` respectively.

## Create the database

An administrator runs the following SQL/psql commands, not Bash. Create roles and databases only if they do not already exist.

```sql
CREATE ROLE tushare_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password tushare_writer
CREATE DATABASE tushare OWNER tushare_writer;
```

Configure `.env`, then run in Bash:

```bash
uv run tushare-downloader init-db
```

Initialization creates `raw` and `meta` objects atomically and prints `database_id`. Repeated initialization validates structure. It does not silently alter incompatible columns, drop tables or take ownership of unrelated objects. Downstream `analysis` objects are user-managed.

## Read-only access

After initialization, an administrator can grant downstream access with SQL/psql:

```sql
CREATE ROLE tushare_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password tushare_reader
\connect tushare
GRANT CONNECT ON DATABASE tushare TO tushare_reader;
GRANT USAGE ON SCHEMA raw TO tushare_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO tushare_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE tushare_writer IN SCHEMA raw
  GRANT SELECT ON TABLES TO tushare_reader;
```

## Inspect and maintain

These queries describe local rows; minimum and maximum dates do not prove there are no gaps:

```sql
SELECT min(trade_date), max(trade_date), count(*)
FROM raw.daily_basic WHERE NOT _is_stale;
SELECT trade_date, count(*) FROM raw.daily_basic
WHERE NOT _is_stale GROUP BY trade_date ORDER BY trade_date;
```

Use `fetch ... --dry-run` for request coverage decisions. Keep PostgreSQL autovacuum enabled. After large imports, use `ANALYZE raw.daily_basic` when needed; routine maintenance may use `VACUUM (ANALYZE) raw.daily_basic` outside a transaction. The downloader does not run VACUUM FULL automatically.

## Explicit cleanup

```bash
tushare-downloader clean daily_basic
# Destructive: use the exact identity returned by the preview only when deletion is intended.
tushare-downloader clean daily_basic --apply \
  --confirm-database tushare --confirm-database-id 'REPLACE_WITH_PREVIEW_UUID'
```

Cleanup removes all raw rows and block records for the API, not only stale rows. Both database name and UUID must match. Downstream foreign keys may prevent deletion; cleanup then fails atomically without cascading. Make a [backup](backup-restore.md) first if the data must be retained.
