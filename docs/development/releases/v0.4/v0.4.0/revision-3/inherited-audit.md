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
| B02 | Pass | Seven real-DB cases assert actual requested params and stored values for valid skip, rows without observations, old spec, failed attempt, inconsistent local counts, enlarged bounds and expired empty observation. Combined with empty-age boundary tests, only valid records skip. |
| B03 | Pass | Distinct last_success_at/last_reconciled_at tests verify reconciliation controls refresh and missing reconciliation requests again; age before/equal/after and force-priority tests pass. Real wrong-closed-calendar integration proves force still respects filtering unless explicitly bypassed. |
| B04 | Pass | test_empty_recheck_boundary_and_force_priority checks before/equal/after expiry for fetch/refresh and force priority; planning reads slice observation timestamps, not raw row timestamps. |
| B05 | Pass | test_update_uses_latest_date and Shanghai-midnight/future-latest clipping tests cover lagging latest date, inclusive lookback, empty local data refusal and snapshot bypass; update request_reason always requests. |
| B06 | Pass | Six real-DB command/initial-state cases prove fetch skips an existing valid snapshot, refresh/update request L/D/P/G/UN and reconcile missing rows, and all commands work from an empty snapshot. An extreme lookback setting has no effect; no date args or lookback appear. Existing request-type matrix proves requested fetch does not reconcile missing keys. |
| B07 | Pass | test_provisional_success_is_rechecked_after_stable_endpoint advances the clock and checks request selection; failure_keeps_committed_days_and_rerun_only_retries_gap verifies ordinary rerun from persisted database facts. |
| C01 | Pass | Fixed-address tests cover negative floor boundaries, exact endpoints, multi-block availability clipping and explicit ordered unique blocks crossing the origin; observation range expansion/spec changes force requests. Actual requested bounds persist in Store slice records. |
| C02 | Pass | test_basic_and_bypass_have_no_external_access uses a forbidden client, asserts weekday requests/weekend filtering and snapshot exemption; integration calendar_default_filters_weekend verifies persisted dates. |
| C03 | Pass | test_valid_calendar_overrides_weekend_and_cache_age_equal uses an explicit SSE cache with Saturday open and weekdays closed, checks the exact requested/filtered dates. |
| C04 | Pass | Cross-year test checks one query per year, cache age equality and expiry; numeric/calendar validation and future/incomplete-cache refusal tests pass. filter_requests copies parsed days into a fixed result and delegates finite retry solely to TushareClient; cached-result test survives external cache modification. |
| C05 | Pass | Four real-DB preparation-failure fixtures cover network/business/missing dates/cache-write failure: exit 1, only trade_cal called, no data/observation writes and explicit bypass guidance; invalid calendar configuration exits via ConfigError. |
| C06 | Pass | force_refresh_bypasses_valid_but_wrong_closed_calendar forbids cache reads during bypass, checks changed stored value and unchanged cache; weekend bypass integration preserves successful local skips. |
| C07 | Pass | New forbidden-read/write/client test establishes empty candidates access nothing; existing basic/off/bypass/snapshot tests prohibit remote access. Filter-only integration creates observations only for requested weekdays; filter code has no database mutation and excluded blocks never reach merge. |
| C08 | Pass | Missing-cache dry-run integration returns 1 with zero data/observation/cache writes; cached dry-run forbids remote client and cache writer, retains original bytes and exact dates. Basic/off skip cache logic; ordinary dry-run integration confirms no source-data writes. |
| D01 | Pass | test_at_row_limit_is_success asserts HTTPS/no redirects; business error with attached rows rejects before parsing; transient/nonretryable HTTP tests classify status independently. Executor never merges a failed query. |
| D02 | Pass | Real client with fake clock: network exhaustion and new 429/500/502/503/599 matrix each stop at four attempts; every HTTP attempt paced at ten-second intervals; Retry-After and over-budget refusal plus business/TLS/protocol/parameter nonretry rules inspected. |
| D03 | Pass | Shared parser tests assert reordered fields, leading-zero text, Decimal/date conversion, missing/duplicate field rejection, invalid booleans/nonfinite decimals/dates/row widths. Four actual daily-contract cases share the parser; real PG storage tests confirm Decimal and SQL NULL overwrite behavior. |
| D04 | Pass | Parser identical duplicates count separately and conflicting same keys fail. Snapshot cross-status conflict and buffer-overflow cases stop retrieval before merge, while actual partial-failure execution leaves no snapshot rows. Response-byte limit fails before parsing; suspend conflict integration preserves its entire prior day. |
| E01 | Pass | Real storage tests cover inserts, NULL replacement, stale/reactivation, unchanged source _updated_at with advanced _last_seen_at; duplicate failure and wire COMMIT-loss tests compare raw rows and meta observations atomically. |
| E02 | Pass | Real-DB test_failure_keeps_committed_days_and_rerun_only_retries_gap and business-error stop, plus four consecutive-failure threshold/reset cases assert committed counts and unattempted summaries. |
| E03 | Pass | snapshot_statuses_merge_stale_and_reappear verifies L/D/P/G/UN order; snapshot_partial_failure_is_not_merged asserts zero writes and later Not attempted; cross-state duplicate conflict stops retrieval before merge. |
| E04 | Pass | Single-state empty/full nonempty fixture commits; empty_snapshot_retains_existing_rows_without_reconciliation preserves old rows and clears complete reconciliation; partial retrieval and conflict tests never dispatch a merge. |
| E05 | Pass | Command/type matrix confirms only refresh or mutable update reconcile missing keys; all four new daily APIs and daily_basic preserve append-only update. New five-API SQL tests compare complete outside-date and other-table rows unchanged and verify same-key reactivation. Existing snapshot tests cover full-source stale/reappearance. |
| E06 | Pass | test_real_commit_confirmation_loss cuts actual PostgreSQL protocol before COMMIT or hides completed reply; both report unknown while independent connections prove distinct commit states; executor unknown test stops remaining requests without confirmed-row credit. |
| E07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E09 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F04 | Pass | Reporter writes a temporary file and replaces report.md before execute constructs the data client; before report marks Final result: not recorded. Atomic-replacement tests preserve Original plan; real SIGKILL test observes that plan after one commit and before the second response. Final results/attention precede the retained plan. |
| F05 | Pass | Initial report failure prevents requests; final Path.replace failure preserves original bytes; missing final file test confirms no report is published. Report path is printed only after successful replacement. Real SIGKILL integration preserves the uncompleted plan and already committed row without claiming completion. |
| F06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G01 | Pass | Reporter creates JSONL and emits invocation_started before echoing the path; CLI constructs Reporter before connect/calendar execution. Canonical-directory tests inspect this order; quiet/plain tests retain the path and static help tests create no files. |
| G02 | Pass | test_six_modes_preserve_requests_database_and_report now covers all six APIs × success/empty/partial × six modes (108 executions). It compares actual request lists, stored source/stale rows, exit codes and normalized complete report; checks quiet errors/paths and plain controls. Separate read-command tests preserve active query bodies and partial warnings. |
| G03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G06 | Pass | Fake-clock tests now prove 20-block rolling window, five-sample/ten-second thresholds, retry/commit/stall suppression and zero-plan no Live. Existing four-Hz shared-budget test covers both block and worker ticks; calendar preparation runs before data progress starts. |
| G07 | Pass | Rotation test independently parses all pieces and compares event sequence 0..19; final-events test checks report links include late-created parts. Event code retains critical non-DEBUG events irrespective of quiet; existing marker checks cover secrets. Log paths now follow command subdirectories. |
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
| L05 | Pass | suspend_d parser fixture deduplicates equal keys and raises duplicate_conflict for unequal events. Actual executor conflict case preserves old day and reports failure; three-command daily test changes S to R across requests successfully. Empty-response mode matrix verifies its special explanation and no missing-key reconciliation. |
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


## Planning and calendar boundary audit

Four additional tests distinguish reconciliation freshness from a later fetch, verify
ordered negative/zero/positive fixed blocks with clipped physical bounds, forbid any
calendar access for empty candidates, and prove a cached dry-run performs neither
requests nor writes. Its already-selected dates remain fixed after external cache edits.

The planning/calendar suites passed **46 cases in 0.21s**; Ruff passed. Source review
also checked a single finite HTTP retry layer and the filter-to-executor boundary.
Together with the previously inspected real database filtering/dry-run tests, these
close B03 and C01/C04/C07/C08 in the inherited audit. No production behavior changed.
Other request/snapshot/report and cross-feature conditions retain their own statuses.


## Report, log and ETA evidence review

Progress/report/metric suites passed **29 tests in 0.49s**, including two new tests
for the rolling 20-block window, a five-sample duration below ten seconds and a zero
plan with no Live/worker. Existing tests cover retry/commit/stall suppression, four-Hz
refresh, rotation, late report links and atomic replacement. Source ordering was
checked against previously run real SIGKILL and report-failure integration cases.

This closes F04/F05/G01/G06/G07 in the inherited audit. It does not stand in for the
remaining six-mode snapshot coverage or human terminal layout. No production code
changed; Ruff and format checks passed.


## Six-mode snapshot comparison

The real PostgreSQL output-mode suite now includes stock_basic, alongside all five
dated datasets. Eighteen success/empty/partial scenarios each run Rich/plain ×
quiet/normal/verbose: **108 executor runs**, reported as **18 passed in 4.88s**.
Each compares request parameters, stored source/stale values, exit status and full
report semantics after removing legitimate time/path differences.

The snapshot cases additionally assert L/D/P/G/UN request order; partial failure stops
after D with zero committed rows, empty yields zero rows, and success commits five
fixture rows. Reports explain subrequests are not independently committed and omit
lookback. Quiet retains errors and paths; plain output contains no terminal controls.

This closes G02 with the separate active-query body tests. The fake TTY streams exercise
the actual renderers but do not constitute Windows Terminal human layout acceptance.
No production code changed; Ruff passed.


## Fetch observations and snapshot command audit

Six snapshot cases cover fetch/refresh/update from empty and seeded databases;
lookback=999 does not affect snapshot requests. Existing valid fetch skips; refresh
and update request all five states and mark the missing old key stale. The complete
snapshot/type-matrix suites passed **23 cases in 2.18s**.

Seven daily fetch cases use persisted database observations: valid records skip,
while missing records despite existing rows, old specs, recorded failure, inconsistent
counts, expanded scope and expired empty records re-request the exact day. Stored
values independently confirm whether a request was applied. The full download module
passed **24 cases in 3.13s**. These close B02/B06 with existing boundary/matrix evidence.
No production behavior changed; Ruff passed. Fixtures were isolated from production.


## Daily dataset protocol and reconciliation audit

New cross-scope PostgreSQL tests run for daily_basic/daily/adj_factor/stk_limit/suspend_d.
After reconciling one date, complete rows at another date and in stock_basic compare
unchanged, including managed timestamps. Reappearing keys reactivate instead of
creating a new identity. Existing command matrices establish which commands may
perform that reconciliation.

The actual API parser, shared client and daily expansion suites passed **56 cases in
3.04s**; Ruff passed. Reviewed assertions cover field ordering, typed values, conflicts,
empty results, additive initialization preservation/rollback and request scope. This
closes D03/D04/E05/L05 using the additional previously inspected storage/snapshot tests.
It does not claim a fresh old-software upgrade or real Tushare smoke run; those keep
their own evidence requirements. No production behavior changed.
