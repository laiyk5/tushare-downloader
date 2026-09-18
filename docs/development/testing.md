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

## Local feedback order

Run checks in increasing cost order. Stop a diagnostic run on its first failure; fix it before
continuing. Batch related edits instead of restarting the database and full suite after each edit.

| Stage | Checks | Trigger |
| --- | --- | --- |
| 1 | Ruff and affected configuration/static checks | Each coherent edit batch |
| 2 | Previously failing cases and directly affected tests | During a fix |
| 3 | Complete unit suite | A coherent change is ready for regression |
| 4 | Affected PostgreSQL integration modules | Storage, execution or database-facing behavior changes |
| 5 | Real process, authentication, deadline and recovery tests | Their shared core or boundary changes |
| 6 | Full required regression, package build and affected documentation checks | Stable candidate after implementation changes |

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
# Replace this example module with the affected tests. Keep the first run focused.
uv run --locked pytest tests/unit/test_config.py -x
uv run --locked pytest tests/unit -x
# Only with all documented isolated integration and cluster fixtures configured:
uv run --locked pytest tests/unit tests/integration tests/cluster --durations=20
```

Last-failed selection (`--lf`) can accelerate diagnosis, but is not a full regression and must not
replace affected tests. Shared config, CLI, reporting and worker changes have broad consumers;
expand selection accordingly. Documentation navigation changes require navigation tests and a
strict site build. Run coverage for a stable candidate or when investigating missing branches,
not on every focused iteration. Capture durations during the next already-required full run;
do not repeat a passing run solely to collect timings.

Keep PostgreSQL tests sequential while fixtures share and recreate raw/meta schemas. Do not
apply `-n auto` without independent database isolation. Reuse one disposable server within a
batch while preserving each test's isolation and cleanup. Local work does not require a GitHub run.

Before removing a test, identify its behavior and boundary, the retained test that covers them,
and any requirement-specific loss. Review repeated output/API Cartesian products first; retain
API-specific contracts and real permission, rollback, migration and uncertain-commit boundaries.
Reducing collected case count or splitting files is not itself a speed improvement. Profile before
introducing markers, concurrency or a new test runner; this workflow needs none of them.

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

Acceptance records describe their recorded candidates. Reuse unchanged evidence only with an explicit source comparison and scope; validate changed behavior against the current candidate.
The [acceptance standard](../design/acceptance.md) is maintained in Chinese; measurement methods are in [benchmarks](benchmarks.md).

## Setup validation — revision 4 finalized

The proposed [interactive contract](../design/database-setup-ui.md) replaces the
full-screen frontend with sequential Click prompts and Rich output. Implementation is authorized; fix test expectations from the finalized contract before code changes.

Keep revision 3 source, tests and evidence attached to their original baseline.
First add failing tests for cold startup, Ready without questions,
numbered edits, target confirmation, plain output, --new conflicts, hidden passwords,
EOF/Ctrl+C and partial-result recovery. Retire framework-specific focus and widget tests
only with an explicit mapping to the new requirements; retain database safety tests.

Reuse unchanged setup_service, setup_db, setup_config and bounded behavior with source
comparison and evidence references. Test interactive/headless plan equivalence and
one real isolated end-to-end route through the new adapter. Expand real database tests
only where the shared core changes or evidence is missing. Run one complete required
regression on the stable candidate; browser prototypes are not native-terminal signoff.

## Bounded verification — revision 4 finalized

Use the fixed scope and stop rules in [acceptance O.4](../design/acceptance.md#verification-scope).
Before implementation, map existing reusable evidence, current required checks and human
review to the acceptance IDs. Do not multiply scenarios by every mode, width, role or platform.
A new check needs a concrete failure, missing contractual evidence or relevant source/environment
change, plus a minimal diagnostic and stop condition. Hypothetical improvements belong in backlog.

Close passing checks when their inputs are unchanged. Run focused checks during edits and one
required complete regression on the stable candidate. Repeat affected checks after fixes, not
all historical experiments after documentation updates. Goal continuation does not expand scope.
When only human review remains, report that dependency instead of adding more validation.
