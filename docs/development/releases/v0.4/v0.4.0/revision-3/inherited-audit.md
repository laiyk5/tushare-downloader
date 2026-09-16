# Inherited acceptance audit

Status: **in progress, not accepted**. Candidate production code:
`8a4dd1bd4ab3da3308ac4d944af96eef1b011d9b`; design:
`993d14d4f94d9678f6acb0536e8a8cf512693f05`.

This is the explicit A–J/L audit queue, not a claim that every Not run requirement
lacks tests. The status means the complete requirement has not yet been signed off
against inspected evidence. K is a separate human-authorized release gate.

## Change-impact boundary

Compared with revision 2 candidate `3bb9354f743bd1f2bcbe315d34aa02e02c6c5720`,
revision 3 changes the shared bounded worker, CLI entry, dependencies, setup,
configuration template and documentation. The downloader/storage/inspection/contract
modules themselves are unchanged. This supports bounded reuse of old source-format
and database-layout observations, but **does not** establish runtime equivalence:
CLI, worker and dependency changes still require current regression and affected
performance/terminal checks. Old export-wizard evidence does not verify the new TUI.

Current full regression and installed smoke outputs are linked from the
[implementation record](index.md). No fresh real Tushare request or backup/restore
exercise was performed in this audit checkpoint; their status is not upgraded.

## Requirements

| ID | Status | Evidence or remaining work |
| --- | --- | --- |
| A01 | Pass | Current wheel/sdist build, distribution checker and installed smoke record; Python 3.12 in WSL. |
| A02 | Pass | Current 546-test regression, Ruff and 174-file format check; subsequent test-only addition passed its six-case module. |
| A03 | Pass | test_config.py: explicit selected file, environment/CLI overrides, defaults, cwd-only lookup, literal interpolation, empty override and invalid-value boundaries inspected and passed. |
| A04 | Pass | Grouped template reviewed against config.py; parsing the complete example matches all default Settings fields. Existing duplicate/unknown-key preservation and setup conservative-write tests passed; no production .env was read or rewritten. See configuration-check.json. |
| A05 | Pass | Current .gitignore is byte-identical to v0.3.0; git check-ignore --no-index verifies runtime/cache files ignored and example/lock/design/demo retained. See configuration-check.json. |
| A06 | Pass | New test_database_isolation.py exercises actual fixture/benchmark entry points with missing environment or wrong database/user; poison dotenv is ignored and rejected identities execute no SQL. Other benchmark entry guards reviewed before writes; actual dedicated cluster identity evidence is retained. |
| B01 | Pass | CLI invalid-argument matrix covers missing date pairs, reversed ranges, future dates, snapshot dates and update date/max-age rejection; future-date validation moved before DB connection after a failing regression. |
| B02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B04 | Pass | test_empty_recheck_boundary_and_force_priority checks before/equal/after expiry for fetch/refresh and force priority; planning reads slice observation timestamps, not raw row timestamps. |
| B05 | Pass | test_update_uses_latest_date and Shanghai-midnight/future-latest clipping tests cover lagging latest date, inclusive lookback, empty local data refusal and snapshot bypass; update request_reason always requests. |
| B06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B07 | Pass | test_provisional_success_is_rechecked_after_stable_endpoint advances the clock and checks request selection; failure_keeps_committed_days_and_rerun_only_retries_gap verifies ordinary rerun from persisted database facts. |
| C01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C02 | Pass | test_basic_and_bypass_have_no_external_access uses a forbidden client, asserts weekday requests/weekend filtering and snapshot exemption; integration calendar_default_filters_weekend verifies persisted dates. |
| C03 | Pass | test_valid_calendar_overrides_weekend_and_cache_age_equal uses an explicit SSE cache with Saturday open and weekdays closed, checks the exact requested/filtered dates. |
| C04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C05 | Pass | Four real-DB preparation-failure fixtures cover network/business/missing dates/cache-write failure: exit 1, only trade_cal called, no data/observation writes and explicit bypass guidance; invalid calendar configuration exits via ConfigError. |
| C06 | Pass | force_refresh_bypasses_valid_but_wrong_closed_calendar forbids cache reads during bypass, checks changed stored value and unchanged cache; weekend bypass integration preserves successful local skips. |
| C07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| D01 | Pass | test_at_row_limit_is_success asserts HTTPS/no redirects; business error with attached rows rejects before parsing; transient/nonretryable HTTP tests classify status independently. Executor never merges a failed query. |
| D02 | Pass | Real client with fake clock: network exhaustion and new 429/500/502/503/599 matrix each stop at four attempts; every HTTP attempt paced at ten-second intervals; Retry-After and over-budget refusal plus business/TLS/protocol/parameter nonretry rules inspected. |
| D03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| D04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E01 | Pass | Real storage tests cover inserts, NULL replacement, stale/reactivation, unchanged source _updated_at with advanced _last_seen_at; duplicate failure and wire COMMIT-loss tests compare raw rows and meta observations atomically. |
| E02 | Pass | Real-DB test_failure_keeps_committed_days_and_rerun_only_retries_gap and business-error stop, plus four consecutive-failure threshold/reset cases assert committed counts and unattempted summaries. |
| E03 | Pass | snapshot_statuses_merge_stale_and_reappear verifies L/D/P/G/UN order; snapshot_partial_failure_is_not_merged asserts zero writes and later Not attempted; cross-state duplicate conflict stops retrieval before merge. |
| E04 | Pass | Single-state empty/full nonempty fixture commits; empty_snapshot_retains_existing_rows_without_reconciliation preserves old rows and clears complete reconciliation; partial retrieval and conflict tests never dispatch a merge. |
| E05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E06 | Pass | test_real_commit_confirmation_loss cuts actual PostgreSQL protocol before COMMIT or hides completed reply; both report unknown while independent connections prove distinct commit states; executor unknown test stops remaining requests without confirmed-row credit. |
| E07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E09 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G08 | Pass | test_real_log_device_failure_after_commit_preserves_data uses /dev/full at slice_result: nonzero exit, committed row retained, next request absent and accurate report. Separate before/final-report fault tests distinguish report failure. |
| G09 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| J01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| J02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| J03 | Pass | Current integration and isolated cluster runs use WSL Python to Windows PostgreSQL 18 on port 55433; fixture identity guards inspected. |
| A01 | Pass | Current wheel/sdist build, distribution checker and installed smoke record; Python 3.12 in WSL. |
| L01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |

## Added v0.4 requirements

- M01–M04: inspect LG/UP/W/DL subconditions and original local evidence;
  rendered browser navigation and old-URL checks remain separate from link validation.
- N01: inspect IN01–IN09. Current timestamp tests add evidence for IN02/03/06;
  permission, partial-result, budget, six-mode and human-layout conditions remain
  composite requirements. Revision 2 benchmark cannot silently cover a changed worker.
- N02: inspect DA01–DA08 and SC01–SC08. Current real cluster tests provide
  permission and old-database evidence, but must be mapped to each full condition.
- N03: current complete regression and actual old-source fixture supplement the
  cross-feature guarantee; English guide/SQL and terminal checks still need mapping.
- O: see the [setup audit](acceptance-audit.md), including its explicitly open
  Windows Terminal + WSL human routes.

## Request-contract audit update

Source and assertion review covered test_config.py, test_client.py, test_planning.py,
test_calendar.py, test_cli_scaffold.py, test_cli.py, test_download.py and
test_acceptance_matrix.py. Passing statuses above cite actual cases; nearby unreviewed
composite conditions stay Not run. New HTTP pacing cases passed. A new CLI case
first failed because future dates reached the database connection; the CLI now rejects
them before reporter/database construction, retaining the planner's defensive check.
The full unit regression after the repair passed; see the implementation record.
Current full integration/distribution evidence predates this CLI-only repair and must
be refreshed for the final candidate. No source data protocol or database DDL changed.

## Storage and report fault review

The storage, real wire faults, snapshot, output faults, output modes and CLI integration
modules were rerun after candidate `759d77b`: **42 passed in 7.71s**. Additional
assertions confirm unchanged rows advance observation time and a wrong database UUID
cannot clean raw/meta state. Ruff passed. PostgreSQL remained confined to the guarded
port-55433 test cluster; no production configuration or remote API was used.
E07/E08 and F/G composite conditions not fully mapped remain open despite these results.


## Inspect fixes superseding the earlier unchanged-module assumption

The later Inspect audit changed inspection.py (persistent old-spec explanation) and
cli.py (interruption exit 130). The earlier revision-2 comparison describes the state
at that checkpoint, not these subsequent fixes. New real-DB and six-output-option
tests cover the warning; an interruption test preserves prior dataset output and
stops before the next dataset. Full unit/integration regression: 508 passed in 32.63s.
Performance and human layout sign-off must account for the new explanation field;
no earlier benchmark or screenshot automatically verifies it.


## Inspect independent-field failures

Four real PostgreSQL cases inject server SQLSTATE 42501/57014 at either the space
query or success-time query. These are explicit server-error injections, not claims
of actual permission revocation or elapsed timeout. They abort the real transaction;
the production savepoint recovery keeps the installed schema, latest date, attempt
time and exact counts, marks the failed field Unavailable/Timed out, and returns
Partial inspection. Metadata remains unchanged. A failure in a later metric also
preserves the earlier space result.

Six CLI option combinations verify the partial result remains visible, stderr reports
Partial inspection, exit code is 1 and no files are created. This tests option semantics
with captured output, not a real Rich terminal layout.

The complete affected Inspect suites passed **37 tests in 1.95s**; Ruff passed.
No production code changed. This supplies additional IN04/IN05/IN07 evidence but
does not complete real permission, lock-wait, deadline or human-layout subconditions.


## Inspect real DDL lock waits

Two independent connections now verify real ACCESS EXCLUSIVE locks on meta.schema_info
and raw.daily. The lock is acquired before inspection starts, so synchronization does
not depend on sleeps. Inspection uses a one-second query budget and one-second
connection budget; both cases finish within the combined budget plus the documented
two-second termination allowance. No new multiprocessing child survives, and a fresh
inspection succeeds after the lock transaction ends.

The metadata case initially returned Unavailable with SQLSTATE 57014. The adapter now
classifies that explicit worker SQLSTATE as Timed out; SQLSTATE 42501 remains Permission
denied. Raw-table metric timeout continues to retain its partial fields. No query replay
or mutation was added.

The full affected Inspect integration/CLI suites passed **39 cases in 5.12s**; Ruff
passed. This establishes actual lock-wait/deadline recovery, rather than treating the
earlier injected 57014 error as elapsed-time evidence. The broader IN05 gate still
needs its concurrent writer and interruption subconditions mapped; human terminal
acceptance remains independent.
