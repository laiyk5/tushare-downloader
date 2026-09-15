# tushare-downloader

Download Tushare Pro data into PostgreSQL, one table per API. Supports `daily_basic`, `stock_basic`, `daily`, `adj_factor`, `stk_limit` and `suspend_d`, with bounded retries, request deduplication, incremental updates and source reconciliation.

- [Quick start](docs/guide/quickstart.md)
- [Configuration](docs/guide/configuration.md)
- [Download and update](docs/guide/downloading.md)
- [CLI reference](docs/reference/cli.md)
- [Online documentation](https://laiyk5.github.io/tushare-downloader/)

## Get started

Use Python in WSL/Linux and a reachable PostgreSQL database. From the repository:

```bash
uv sync --locked
if [ ! -e .env ]; then cp .env.example .env; fi
chmod 600 .env
# Edit .env with your Tushare token and PostgreSQL connection settings.
uv run tushare-downloader list
uv run tushare-downloader init-db
uv run tushare-downloader fetch daily_basic -s 2024-01-02 -e 2024-01-05
uv run tushare-downloader update stock_basic
```

The database and role must exist before `init-db`; see [database setup](docs/operations/database.md).

Use `fetch` to fill a range, `refresh` to reconcile corrections and `update` to follow the API's update policy. Preview a download with `--dry-run`. The five daily APIs skip weekends by default; `--ignore-calendar` explicitly bypasses trading-day filtering.

The CLI prints the log path before connecting to the database. Each invocation writes a single `reports/<run>/report.md`, containing the original plan and final results. Rich output is used in interactive terminals; `--plain` selects plain text.

Independent date blocks commit separately: failures retain earlier commits. Snapshot requests merge atomically. Successful API responses do not prove business completeness. There is no background service or resume protocol; rerun a normal command after addressing a failure.

## Contributing

See the [development setup](docs/development/setup.md), [tests](docs/development/testing.md) and [design](docs/design/index.md). Release evidence is maintained under [development](docs/development/acceptance-v0.2.0.md).

## License

Original project code and documentation use the [MIT License](LICENSE). Third-party components retain their own licenses.

The code license does **not** grant rights to redistribute Tushare data. Data access, use and redistribution remain subject to the applicable provider terms and permissions.
