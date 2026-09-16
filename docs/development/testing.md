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

## Setup validation — revision 3 design

The draft contracts are [DBW](../design/database-setup.md), [UI01–UI04](../design/database-setup-ui.md)
and [H01–H08](../design/database-setup-headless.md). Design approval precedes new tests and implementation.
Keep revision 2 evidence attached to its original baseline. DBW09 script-export acceptance is removed
from this revision; historical tests/evidence are not retroactively labelled passed or rewritten.

First test the shared facts, classifications, finite plans, credentials and exit codes, then failure
boundaries and JSONL redaction. Verify headless without a TTY before connecting the Textual frontend.
Both frontends must produce the same plan for identical facts; do not duplicate SQL expectations in
widgets. Add Textual focus, stale-worker-result and cancel tests, followed by real terminal checks
at 40/80/120 columns. The browser prototype is not terminal acceptance evidence.

Use real SCRAM authentication for missing/wrong/correct passwords; trust fixtures remain useful
for unrelated cases but cannot prove password rejection. Cover new and existing roles, cluster-wide
privileges, exact owner checks, repeated application, every partial-commit boundary and uncertain
outcomes. Test reader writes only on disposable objects, never user data. Configuration and logging
tests cover private permissions, ambiguous syntax, concurrent writes, secret exclusion and failure.

Cluster tests remain separate from ordinary integration tests. Require an explicitly identified
disposable server and match SETUP_TEST_DATA_DIRECTORY before mutation; use randomly named test-owned
objects and remove only those. Never load production .env or use elevated ordinary tushare_test
fixtures. Existing harness inputs are SETUP_TEST_ADMIN_URL, SETUP_TEST_DATA_DIRECTORY and
SETUP_TEST_PSQL; these are test inputs, not product headless credentials.

Run the affected ordinary CLI/download/schema regression after frontend integration. Update the
English user documentation only to describe implemented and verified commands. Record exact source
state, database fixture, executed checks and remaining human/release checks separately.
