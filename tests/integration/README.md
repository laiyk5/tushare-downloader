# Integration tests

These tests use real PostgreSQL and synthetic API responses, without requesting Tushare.
The default `uv run pytest` runs unit tests only. Supply a dedicated database to run this directory:

```bash
TEST_DATABASE_URL='postgresql://tushare_test:TEST_PASSWORD@localhost:55432/tushare_test' \
  uv run pytest tests/integration
```

Both database and role must be tushare_test. Missing or mismatched settings fail without production fallback.
Tests remove raw/meta schemas, so this database must be disposable. CI uses a temporary PostgreSQL service.
Never put production credentials in TEST_DATABASE_URL. The example port need not have a running server.
