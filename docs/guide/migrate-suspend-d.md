# Upgrade suspend_d

The current candidate uses dataset schema 2.0.0 (API spec 2). Its key is
`(ts_code, trade_date, suspend_type)`: a suspension and a resumption can occur
on the same day. Other dataset schemas are unchanged.

Stop other writers and back up the database before applying. PostgreSQL tools do not
read the project's `.env`; configure the same PGHOST, PGPORT, PGDATABASE, PGUSER and
PGSSLMODE in your shell. Use a private PGPASSFILE or password prompt, never a password
in command arguments. Check `psql -X -c 'SELECT current_database(), current_user;'`
and compare the target with the migration preview.

```bash
pg_dump --format=custom --file=tushare-before-suspend-v2.dump
uv run tushare-downloader migrate suspend_d
uv run tushare-downloader migrate suspend_d --apply --confirm-database tushare
uv run tushare-downloader inspect suspend_d
```

Use your actual database name. Preview does not change the database. Applying requires
ownership of raw.suspend_d and meta.schema_info. NULL/blank types, schema drift or
foreign keys that depend on the old key block migration; no rows are silently deleted
and no dependent objects are removed. Table identity, rows and grants are retained.

After migration, fetch your original date range again. Spec 1 observations are not reused;
other datasets retain their coverage. A normal repeated fetch uses the existing freshness
rules. Setup and init-db only direct you to this explicit migration.

If commit acknowledgement is lost, run the preview again to observe the actual state;
do not assume failure or blindly replay operations. To revert software, restore the backup
to a separate database using existing roles and `pg_restore --exit-on-error --single-transaction
--dbname=RESTORE_DATABASE BACKUP_FILE`, verify it, then switch configuration. Do not shrink
the new key in place: newly downloaded S/R pairs would conflict. A backup excludes later writes.
