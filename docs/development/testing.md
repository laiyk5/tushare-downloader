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

## Setup-wizard validation

The [DBW conditions](../design/database-setup.md) define acceptance. Tests now exist in tests/unit, tests/integration and the explicitly isolated tests/cluster; the [local evidence](releases/v0.4/v0.4.0/revision-2/index.md) distinguishes executed checks from remaining conditions. For each change, encode independent expectations and observe the expected failure before fixing the implementation.

- Unit tests: intent selection, plan differences, no-write inspection, confirmation refusal, non-interactive input, configuration precedence, secret redaction and safe SQL/psql rendering.
- Filesystem tests: preserve comments and unrelated settings, reject ambiguous duplicates, detect concurrent edits, use restricted permissions and atomic replacement, and retain the old file on failure.
- Isolated cluster tests: create real roles/databases, connect separately as administrator/writer/reader, compare direct and exported-script outcomes, inject failure at each commit boundary, and rerun from the resulting database state.
- Reader tests: prove writes are rejected using disposable tables, including an updatable view; do not run write probes against a user's real tables. Standard online verification uses SELECT and effective-permission checks.
- Upgrade tests: use the actual v0.3.0 baseline and existing candidate schemas, preserve data/identity/user views, and distinguish no migration from unsupported versions.
- Manual checks: real terminal at 40/80/120 columns, hidden password entry, cancellation and partial-result clarity. A captured mock transcript alone is not evidence of usable interaction.

Cluster tests need a separate opt-in harness with an explicitly supplied disposable endpoint and ownership checks; they must never be added to the ordinary tushare_test fixture with elevated credentials. Define that harness and its refusal tests before any cluster mutation test. Do not load production .env or perform broad role/database cleanup. Record exact objects and remove only those created by the test in its isolated cluster. A database failure and a later configuration-save failure are separate outcomes; assert both rather than expecting one global rollback.

No current DBW condition requires a general migration engine or a real structural migration. Use unknown-version fixtures to test rejection. Keep existing runtime acceptance evidence attached to its original software/design baseline; new setup functionality needs new evidence.

The final wizard review adds explicit DBW cases for empty versus unmanaged databases, cluster-shared roles, unsupported ordinary DATABASE_URL, per-key environment overrides, missing configuration targets, client-side deadlines and the four-step export bundle. Validate exported preconditions and actor identities; an unverified export must not apply mutations. Test expiry during DNS/network/COMMIT waits as well as server statement timeout. These are test requirements, not existing test results.

## Run isolated setup tests

Setup cluster tests live in `tests/cluster`, separate from ordinary integration tests and their CI job.
They require SETUP_TEST_ADMIN_URL, SETUP_TEST_DATA_DIRECTORY matching the server's actual data directory,
and SETUP_TEST_PSQL pointing to psql. Run `uv run pytest tests/cluster` only against a disposable cluster.
The fixture checks identity before mutation and uses random test-owned role/database names.
Do not supply the production server's path as a shortcut to satisfy the guard.
