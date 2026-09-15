# Testing

Use equivalence classes and boundary analysis. A finite test suite does not prove correctness for every input.
Unit tests require neither real credentials nor an external database; transaction, COPY and commit-failure tests use PostgreSQL.

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit --cov=tushare_downloader --cov-branch
uv build
```

By default, `uv run pytest` collects only tests/unit. Coverage identifies missed branches; it is not an arbitrary release percentage target.

## PostgreSQL integration tests

Create a dedicated `tushare_test` role and database. The role must be able to manage test objects.
Tests delete raw/meta schemas in that database. Never use a production database.
Port 55432 below is an example, not a promise of a running service.

```bash
TEST_DATABASE_URL='postgresql://tushare_test:TEST_PASSWORD@localhost:55432/tushare_test' \
  uv run pytest tests/integration
```

The fixture reads the process environment directly and does not load `.env`.
Both database and user must be named tushare_test; missing configuration fails explicitly.
Tests cover command policies, block transactions, stale/reactivation, retrying failed ranges,
real disconnects before/after COMMIT, pg_terminate_backend, Ctrl+C, output failures and the writer lock.
Daily API expansion also requires additive initialization and rollback tests that preserve existing data and observations.

GitHub Checks runs unit tests, isolated wheel installation and PostgreSQL 18 integration tests on Ubuntu.
Local validation additionally covers WSL Python connecting to Windows PostgreSQL; native Windows Python is outside acceptance scope.
Record real Tushare smoke requests and performance measurements separately. Never embed tokens in fixtures.

Acceptance records are historical evidence, not substitutes for running the current candidate.
The [acceptance standard](../design/acceptance.md) is maintained in Chinese; measurement methods are in [benchmarks](benchmarks.md).
