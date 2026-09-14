# Quick start

Use Python 3.12 in WSL/Linux, uv, a reachable PostgreSQL 18 server and a Tushare Pro token with permission for the selected API. PostgreSQL may run on Windows. Ask the database administrator to complete [database setup](../operations/database.md) first.

```bash
git clone git@github.com:laiyk5/tushare-downloader.git
cd tushare-downloader
uv sync --locked
if [ ! -e .env ]; then cp .env.example .env; fi
chmod 600 .env
```

Edit `.env`: set `TUSHARE_TOKEN`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD`. Defaults are database `tushare` and role `tushare_writer`. Keep credentials local; do not overwrite an existing configuration. See [all settings](configuration.md).

```bash
uv run tushare-downloader list
uv run tushare-downloader init-db
uv run tushare-downloader fetch daily_basic -s 2024-01-02 -e 2024-01-05 --dry-run
uv run tushare-downloader fetch daily_basic -s 2024-01-02 -e 2024-01-05
```

`list` needs no database or token. `init-db` creates and validates managed objects. Dry-run reads the local database and writes a plan, but does not request Tushare data or modify the database. In calendar mode it requires a valid existing calendar cache; basic mode has no external calendar dependency.

Actual requests consume API quota. The terminal prints log and report paths. A repeated fetch skips valid successful blocks; rerun failed ranges after addressing their cause. See [download and update](downloading.md) for daily updates, source corrections and empty responses.
