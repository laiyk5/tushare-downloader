# Quick start

Use Python 3.12 in WSL/Linux, uv, a reachable PostgreSQL 18 server and a Tushare Pro token with permission for the selected API. PostgreSQL may run on Windows. Use the [setup wizard](database-setup.md) for the database connection and accounts, or ask an administrator to follow [manual database setup](../operations/database.md).

```bash
git clone git@github.com:laiyk5/tushare-downloader.git
cd tushare-downloader
uv sync --locked
if [ ! -e .env ]; then cp .env.example .env; fi
chmod 600 .env
```

Set `TUSHARE_TOKEN` in `.env`. Run `setup` below in an interactive terminal to enter the server connection, review necessary database/account changes and separately save the connection settings. PostgreSQL must already be running; the wizard can request temporary administrator credentials when needed. Defaults are database `tushare` and role `tushare_writer`. If an administrator prepared the database, you can instead set `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD` directly. Keep credentials local and retain existing configuration. See [all settings](configuration.md).

```bash
uv run tushare-downloader list
uv run tushare-downloader setup
uv run tushare-downloader fetch daily_basic -s 2024-01-02 -e 2024-01-05 --dry-run
uv run tushare-downloader fetch daily_basic -s 2024-01-02 -e 2024-01-05
```

`list` needs no database or token. `setup` inspects the database and proposes only necessary changes. For manual setup, `init-db` creates and validates managed objects in an existing database. Dry-run reads the local database and writes a plan, but does not request Tushare data or modify the database. In calendar mode it requires a valid existing calendar cache; basic mode has no external calendar dependency.

Actual requests consume API quota. The terminal prints log and report paths. A repeated fetch skips valid successful blocks; rerun failed ranges after addressing their cause. See [download and update](downloading.md) for daily updates, source corrections and empty responses.

Already using an older version? See [Upgrade](../operations/upgrading.md) before following first-time database setup.

To query downloaded tables from PostgreSQL or Excel, follow [Read your data](reading-data.md) using a separate reader account.
