# Upgrade

## v0.3.0 to v0.4.0

This guide describes the v0.4.0 candidate. Use the release-tag commands below only after that version is published. Before publication, contributors validate the exact candidate commit in an isolated environment.

The six existing API tables and their schema, keys and permissions remain unchanged. Keep your existing database and connection settings. **No database migration or mandatory init-db run is required.** Existing rows, stale flags and download observations remain available.

New downloads write logs under LOG_DIR/fetch/, LOG_DIR/refresh/ or LOG_DIR/update/. Short command aliases use the full command's directory. Reports remain under REPORT_DIR/<run>/report.md. Old logs are not moved or removed; old reports still reference their original files. Adjust scripts that assume every JSONL file is directly under LOG_DIR. The CLI prints the actual log path before database or remote work begins; reports list all rotation parts. A single-file tail does not follow newly rotated files automatically.

## Before updating

Stop your downloader's active writes, not the PostgreSQL service. Record your current version and keep your configuration. Save any local Git changes before switching revisions; do not discard them with reset --hard. Maintain your existing backup policy. This release does not require a new full backup solely for the software update; future schema migrations require a verified recovery plan first.

For a source checkout, after v0.4.0 is published:

```bash
git status --short
git fetch origin tag v0.4.0
git switch --detach v0.4.0
uv sync --locked
uv run tushare-downloader --version
```

Run from the directory containing your existing .env, or use the existing --env-file option. Do not replace .env with .env.example. PGHOST/PGPORT/PGDATABASE/PGUSER and other supported settings retain their precedence; relative output paths remain relative to the working directory. Never print credentials while checking settings.

## Verify the existing database

Initialization is optional for this upgrade; it validates managed tables:

```bash
uv run tushare-downloader init-db
uv run tushare-downloader list
```

Do not create a replacement database or run clean. The API list confirms software support, not database initialization. With a database client connected to the original database, these are **SQL** checks:

```sql
SELECT database_id, schema_version, specs FROM meta.schema_info;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'raw' ORDER BY table_name;
SELECT api, count(*) AS observations FROM meta.slices GROUP BY api ORDER BY api;
SELECT max(trade_date) AS latest_date FROM raw.daily WHERE NOT _is_stale;
```

Compare database identity and existing observations with your baseline. Counts and maximum dates are useful checks, not proof that every row is unchanged or complete. Large counts may be expensive. Use your existing reader account to confirm its regular queries still work; existing raw queries require no additional grants. Inspect also needs USAGE on meta and SELECT on meta.schema_info/meta.slices; setup can propose that permission change for confirmation. Background on permissions for future new tables is in [database maintenance](database.md).

Optionally preview an already downloaded historical range:

```bash
uv run tushare-downloader fetch daily --start 2026-08-03 --end 2026-08-07 --dry-run
```

This writes a local log and report, but makes no data request or database modification. In calendar mode an insufficient cache may leave the plan incomplete; follow the stated calendar policy rather than treating that as an upgrade failure.

## Failures and recovery

If dependency synchronization fails, fix the software environment before using the database. If optional init-db detects an incompatible identity or structure, investigate without deleting tables; it does not silently migrate incompatible schemas. When commit confirmation is lost, inspect actual database state before retrying or claiming rollback.

If recovery is needed, [restore to a separate database](backup-restore.md), validate data and permissions, then deliberately change the connection. Restoring a backup loses changes made after that backup. No automatic downgrade or down migration is provided; do not assume an older binary accepts a newer schema.

## Supported starting versions

| Source | v0.4.0 route |
| --- | --- |
| v0.3.0 | Direct software update; no database migration |
| Earlier v0.4.x patch | Not applicable to the first v0.4.0 release |
| Previous major | Not applicable: no earlier major exists before 0.x |
| v0.2.x or older, manually modified schema | Outside this guide; establish a compatible v0.3.0 environment first. No direct route is promised here. |

Upgrade documentation starts with v0.4.0. This release does not retrofit a v0.2.0 → v0.3.0 guide. Future releases identify routes from the previous minor and previous major, including intermediate versions when needed, and distinguish validated paths from unsupported jumps.
