# Upgrade suspend_d

Dataset schema 2.0.0 (API spec 2) uses `(ts_code, trade_date, suspend_type)` so suspension
and resumption can both be stored on the same day. Other dataset schemas are unchanged.
Update downstream queries that assumed one row per stock/day.

## Check and upgrade with setup

Stop other downloader writers and prepare a [verified backup](../operations/backup-restore.md).
Keep the existing database. `setup` reads the installed schema, checks supported steps and
shows the changes before asking for the exact target database name.

```bash
uv run tushare-downloader setup
```

For scripts, check first, then explicitly apply the reviewed plan (replace `tushare` with your
actual database name):

```bash
uv run tushare-downloader setup --headless
uv run tushare-downloader setup --headless --apply --confirm-database tushare
uv run tushare-downloader inspect suspend_d
```

The check returns 4 when changes are required, 0 when ready. Apply requires the confirmation
name for migrations; missing confirmation returns 4 and a mismatched name returns 2, without
changes. Supply temporary credentials with the existing private credentials file only when
needed. See [setup](database-setup.md) for permissions and configuration.

Setup executes supported version steps in order, without requiring you to install each intermediate
software release. Each step is transactional: earlier committed steps remain if a later step fails.
Run setup again to inspect actual state and plan the remaining work. An unknown commit result is
not automatically replayed. An already upgraded database requires no repeated migration.

The writer must own the affected table and metadata. NULL/blank suspension types, incompatible
structures or dependencies on the old key block migration. No rows are deleted or guessed; no
CASCADE or automatic ownership changes are used. Existing rows, table identity and permissions
are preserved. Logs are printed before work starts and written under `LOG_DIR/setup/`.

## Coverage and recovery

After migration, explicitly fetch your original date range again when desired. Old spec 1
observations are retained but are not reused for spec 2; new downloads replace corresponding
block observations using normal rules. Setup makes no Tushare requests or automatic downloads.

PostgreSQL tools do not read the project `.env`. Set the same non-secret PG* target explicitly;
use a protected pgpass file or password prompt. Do not source `.env` or put passwords in commands.

Do not shrink the key in place to downgrade: existing S/R pairs can conflict. Restore the old
backup to a separately named database, verify it and deliberately change your connection.
Data downloaded since that backup will not be present. See [upgrading](../operations/upgrading.md).
