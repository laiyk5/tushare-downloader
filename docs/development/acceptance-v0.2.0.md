# v0.2.0 implementation and acceptance record

Design: `design-v0.2.0` (`248bd3cee2447cea38866dc2c796b31eaf35c34e`).
Implementation branch: `codex/implement-v0.2.0`. Status: **in progress, not accepted**.
The normative checklist remains [design acceptance](../design/acceptance.md).

[Requirement-to-evidence index and remaining checks](acceptance-index-v0.2.0.md).

## Current evidence

- Configuration, English help/runtime text, initial Rich presentation, single report lifecycle and calendar filtering have been implemented.
- On 2026-09-14, 106 unit tests and 42 PostgreSQL integration tests passed together at commit `2e9a83d` (4.85 seconds). This is regression evidence, not proof of all acceptance requirements.
- Environment: WSL Ubuntu 24.04 Python with Windows PostgreSQL 18, loopback TCP port 55432. A temporary cluster uses dedicated database and user `tushare_test`; production data is not used for fault injection.
- Further report changes add per-block decisions/outcomes/attempts/committed rows and snapshot subrequest results. Their evidence belongs to the commit containing this record.

## Remaining work

- Audit all A–K requirements against implementation and tests; terminal six-mode behaviour and full report fidelity still need review.
- Finish calendar fault/cross-year checks, true API validation, benchmark comparisons and English user/operations documentation.
- Verify wheel installation, dependency distribution notices, final CI and Pages deployment against the final candidate SHA.
- Stop and remove the disposable local PostgreSQL cluster after remaining database validation.

Do not interpret a passing regression suite as a completed v0.2.0 release gate. Final evidence must record the final software SHA and disclose any unexecuted checks.


## Real calendar protocol check (2026-09-14)

The first real `trade_cal` call exposed a numeric `is_open` flag that the initial text-only fixture missed. The calendar spec now parses this as numeric, accepts only 0/1, and preserves strict parsing for unrelated API text fields. A regression fixture covers the observed wire representation.

- Source: [Tushare trade_cal](https://tushare.pro/document/2?doc_id=26), `exchange=SSE`, full-year request `20240101..20241231`.
- Candidate range `2024-01-01..2024-01-07`: 4 requested dates, 3 filtered dates.
- Cold cache: 1 HTTP attempt. Repeated hot-cache check: 0 HTTP attempts, same decisions.
- Cache timestamp: `2026-09-14T14:05:58.823301+00:00`; temporary artifact `/tmp/td-v02-calendar-check/tushare-SSE-2024.json`.
- No production database writes or source rows published. This verifies this response and cache behaviour, not permanent calendar accuracy.
- Cross-year requests, expiry equality/one-second-over, numeric protocol and invalid UTF-8 cache tests added. Complete regression: 151 tests passed in the commit containing this entry.


## Real API and PostgreSQL check (2026-09-14)

Software tested: `01d5afc` (full commit available through Git); design unchanged. WSL Python connected to the dedicated Windows PostgreSQL 18 instance on 55432 using only database/role `tushare_test`.

- `daily_basic` fetch for 2024-01-02: 5,329 active rows, 0 stale; repeated fetch: 1 block skipped, 0 data requests, unchanged counts.
- `stock_basic` update: all five required statuses processed, 5,911 active rows, 0 stale; repeated fetch: 1 block skipped, 0 data requests, unchanged counts.
- All four executions returned 0. Raw business rows are retained only in the temporary test database, not published here.
- Local diagnostic artifacts: `/tmp/td-v02-real-validation/summary.json`, logs and single-file reports in that directory. Assertions cross-checked database counts and final JSONL records.
- This verifies observed protocol/typing/writes and rerun behaviour, not source business completeness. Synthetic tests cover deletion, reactivation, rollback and commit-unknown cases.

## Output mode equivalence

`tests/integration/test_output_modes.py` executes Rich/plain × quiet/normal/verbose for successful, empty and partially failed downloads (18 executions). It compares requests, source database rows and full report text excluding run-specific log paths. Plain output contains no ANSI or carriage-return controls; quiet preserves failure diagnostics and paths. This complements, but does not replace, actual terminal visual review.

## Candidate package and calendar report regression (2026-09-14)

Candidate metadata is now 0.2.0; this does not create a release or satisfy the remaining release gates.

- `uv lock`, `uv build`: exit 0; built wheel and source distribution.
- `scripts/check_distribution.py`: exit 0. It checks exact LICENSE content and MIT/version metadata, inspects archive contents, installs the wheel into a temporary Python 3.12.3 environment outside the repository, and executes `--help`, `--version`, and `list` without token/database configuration. All return 0; version is 0.2.0 and both supported APIs are listed.
- Wheel contains only project Python files and distribution metadata; no bundled native libraries, credentials, logs or market data. Runtime dependencies are separate distributions, not embedded in this wheel. This is project artifact evidence, not completion of the documentation-site third-party asset review.
- Complete regression: 157 passed in 5.45 seconds; Ruff check and format check exit 0 (75 Python files).
- Fixed the initial report's Request range group to exclude calendar-filtered blocks. The existing weekend integration case now verifies that January 6–7 are absent from Request while January 5 and 8 remain, in addition to checking actual writes and explicit bypass.

The script and assertions are stored with this record; repeat on the final candidate SHA before release. Current artifact SHA-256 values:

- `tushare_downloader-0.2.0-py3-none-any.whl`: `c7e3c65347c5235612b6cc4cc56cb2cc83364dc8e17e5e1cd79208caf3caa77f`
- `tushare_downloader-0.2.0.tar.gz`: `c968166ad7f54bcff5be21dbdf49b461adabd4fca44b31d298f854449fab75a1`

## Help PTY and English user documentation (2026-09-14)

- Actual Linux PTYs, `TERM=xterm-256color`, 40/80/120 columns and 12 rows: root `--help` exits 0 and emits styled ANSI output. Captured output exposed a 40-column layout issue, now fixed by propagating detected terminal width into Click and Rich. Group descriptions are complete concise sentences instead of truncated summaries. These static help checks do not complete Live/progress visual acceptance.
- Narrow Examples use Bash continuation backslashes. A regression checks every command's examples at all three widths, reconstructing arguments and comparing them with the canonical examples; example lines fit the selected width.
- Local raw terminal captures: `/tmp/td-v02-terminal-help/help-{40,80,120}.ansi`. No credentials or database access was used for these commands.
- Translated the remaining Excel guide into English; it remains an optional downstream example. Added current acceptance and benchmark records to the developer navigation while retaining historical v0.1.0 records.
- Zensical strict build and built-iframe target checker passed after these documentation changes.

## Output benchmark evidence (2026-09-14)

I04 output-mode comparison now has six variants × five runs with fake HTTP, real dedicated PostgreSQL and actual Rich rendering. All 30 runs return 0, make 50 data requests and commit 5,000 rows. INFO/DEBUG log event counts confirm diagnostics were exercised. The script checks renderer selection and plain output controls. Raw samples, environment, timing distributions and limitations are linked from [benchmark results](benchmark-v0.2.0.md#output-mode-comparison). This benchmark does not replace real terminal visual inspection (G05), and the final candidate requires impact review/revalidation.

## Progress refresh budget and unknown-commit conclusion (2026-09-14)

- G06: block completion and the periodic worker previously each refreshed Rich, exceeding the four-Hz budget for fast blocks. Both paths now share a monotonic timestamp under the existing lock. State updates are retained even when drawing is throttled; Live stop still renders the latest final state.
- A controlled-clock regression sends 100 block completions plus 100 worker-style refresh requests in one second and verifies exactly four redraws, at least 250 ms apart, with the final completed count retained.
- E06/F07: an unknown COMMIT outcome now leads with `Commit outcome unknown; stopped without replay`, rather than the generic partial-failure conclusion. Existing fault-injection integration assertions verify the nonzero exit, unknown/unattempted counts and new conclusion.
- Full regression: 159 passed in 5.58 seconds; Ruff check passed. The previous output benchmark measured unthrottled Rich completion redraws, so it remains historical evidence and must be repeated before using its values for the final candidate.

## Independent backup/restore rehearsal (2026-09-14)

Application SHA: `4e4be20` (resolve through Git for the full SHA); design `design-v0.2.0`. Windows PostgreSQL 18, WSL Python 3.12, dedicated temporary server on 127.0.0.1:55432. No production database or data was involved.

- Seeded the dedicated `tushare_test` database with synthetic daily_basic data: two rows, followed by reconciliation leaving one active and one stale. Both raw tables and both meta tables were captured for exact comparison.
- Windows PostgreSQL 18 `pg_dump --format=custom` exited 0. Restored to newly created `tushare_restore_v02_check` using `pg_restore --no-owner --no-privileges --exit-on-error --single-transaction`; exit 0.
- All restored raw/meta values exactly matched the source, including timestamps and database identity. `Store.initialize()` successfully validated the restored schema, column types and primary keys. Active/stale counts remained 1/1.
- Reapplied raw-schema USAGE and table SELECT grants to a temporary non-superuser reader. SELECT succeeded; INSERT, UPDATE and DELETE each raised PostgreSQL InsufficientPrivilege.
- Removed the independent restore database and reader role after verification. Local dump is temporary and contains synthetic fixture rows; no dump is published. [Sanitized assertions](restore-v0.2.0.json).

This supplies the restore and permission portion of E09. The v0.1.0-to-v0.2.0 upgrade smoke check remains separate; this rehearsal alone does not mark all of E09 passed.

## v0.1.0 upgrade smoke check (2026-09-14)

Source release: `ec8057ae58b5bb1848337bdb062b7cfdf18b7ee1` (`v0.1.0`). Candidate: `4a12dea379bd7e632322577c72f0e3275c4b1e56`. Design: `248bd3cee2447cea38866dc2c796b31eaf35c34e`. Environment is the same isolated PostgreSQL 18 / WSL Python setup as the restore rehearsal.

- Exported the actual v0.1.0 Python source from Git into a temporary directory. A separate Python process asserted its package import came from that directory, initialized a newly created `tushare_upgrade_v02_check` database, and wrote synthetic data using the old Store implementation: one active and one stale daily_basic row.
- Current `Store.initialize()` accepted the old schema and both API table definitions without migration; database identity and counts were preserved.
- Current `fetch` recognized the valid old successful record and skipped its block. The injected client factory would raise if any HTTP client were created; execution returned 0.
- Current forced `refresh` changed one row and reactivated the other; SQL confirmed two active rows with the new values. Execution returned 0.
- Loaded the unmodified v0.1.0 `.env.example` with an explicitly empty environment mapping. Missing v0.2.0 settings resolved to `calendar_filter=basic`, `terminal_log_lines=5`, and calendar maximum age 24 hours.
- Temporary source/config/output files and the independent upgrade database were removed. [Sanitized assertions with full SHAs](upgrade-v0.2.0.json).

Together with the independent restore rehearsal, this provides E09's recovery and upgrade smoke evidence. Final candidate changes still require impact review; this is not a claim that arbitrary external schema modifications are compatible.

## Calendar preparation failure integration matrix (2026-09-14)

C05 now has executor + real dedicated PostgreSQL coverage for exhausted network failure, business rejection, missing candidate dates and cache write failure. In all four cases execution returns 1, calls only trade_cal, performs zero data requests, leaves raw rows and meta.slices empty, and reports an incomplete plan with explicit user choices. The missing-date path previously lacked an action hint; all calendar-preparation reports now state that the user can repair the source/cache, select basic/off or explicitly use --ignore-calendar. No automatic fallback was added. Illegal configuration remains covered separately by configuration tests.

`tests/integration/test_download.py::test_calendar_preparation_failure_never_starts_data_requests` contains the four cases. Complete regression: 163 passed in 5.87 seconds; Ruff check passed.

## Output benchmark repeated after refresh correction

At `137a454`, all six variants × five runs passed again with 50 requests and 5,000 committed rows per run. Current samples and summaries replace the older values on the [benchmark page](benchmark-v0.2.0.md#output-mode-comparison); previous evidence remains in Git history. Rich median was 0.889 seconds and plain 0.861 seconds in this fixture; overlapping ranges do not establish a general performance ranking.

## Pull request CI (2026-09-14)

[Draft PR #3](https://github.com/laiyk5/tushare-downloader/pull/3) targets main from codex/implement-v0.2.0. Head checked: `29cc838275709935ea7b983b2d6ed4382d229ec1`.

- [Checks run 34859426854](https://github.com/laiyk5/tushare-downloader/actions/runs/34859426854): success. Both check-ubuntu-latest (locked dependency install, Ruff, unit coverage, build and isolated wheel commands) and integration (dedicated PostgreSQL 18 container) completed successfully.
- [Documentation run 34859427601](https://github.com/laiyk5/tushare-downloader/actions/runs/34859427601): docs-build success, including strict clean build, demo path check and principal pages. Deployment was skipped, as required for a pull request.
- Run and individual job/step conclusions were read through the GitHub connector. The PR was created through the existing authenticated browser after the connector lacked PR-create permission; no repository permissions were changed.

This proves CI for the stated head, not final release acceptance, branch-protection configuration or deployed Pages correctness. PR remains draft while the outstanding acceptance audit is completed. Future candidate commits must have their own successful checks.

## Low-height terminal rendering (2026-09-14)

- Implemented the design's static-event fallback for Rich terminals of at most ten rows. This avoids starting a Live region or progress thread when the activity region cannot fit. Stage and current scope remain visible.
- For taller terminals, the recent-activity region is limited by the available height after the task and detail lines. Long recent-event text is ellipsized in that region; full events remain in JSONL. The newest entries are retained.
- Actual Rich render-line tests cover 40/80/120 columns × 12 rows and 40×24, with 20 long recent events. They assert output fits the height and retains phase, failed count and latest event. An 8-row fallback test asserts no Live/thread and no clear-line controls.
- Full unit/integration regression: 168 passed in 5.68 seconds. A controlled render was also exported to local rich-progress-v02.html. Browser visual inspection of that local file was blocked by browser URL policy; no visual-pass claim is based on it. Real PTY dynamic visual review remains outstanding.

## Actual PTY execution matrix (2026-09-14)

Application `c2c71cb`; real Linux PTYs plus a controlled client and dedicated PostgreSQL benchmark database. Thirteen cases cover 40/80/120 columns, an 8-row terminal, Rich/plain × normal/quiet/verbose, stdout-only/stderr-only redirection, NO_COLOR and TERM=dumb. Three date blocks include one injected network failure; all cases return 1 and confirm two successful commits, one failed block and two active rows. No production requests or data were used.

Plain/degraded cases contain no ANSI or application carriage-return animation; the PTY line discipline's CRLF is normalized for this assertion. Log/report paths and failure diagnostics remain present. The short-terminal case does not emit clear-line controls. [Scenario assertions](terminal-v0.2.0/summary.json).

[Terminal reconstruction](terminal-v0.2.0/pty-progress.png) was built from captured ANSI through pyte and inspected as a local image. It is a monochrome character-state reconstruction, not a native terminal screenshot or HTML demo. Old progress lines are visible above the activity region in some captured frames; stable-frame capture and redraw behavior still need investigation. Therefore this evidence proves execution/control-sequence behavior but does not close G05 visual acceptance. Raw captures remain locally under /tmp/td-v02-pty; the exported HTML was not opened through a browser workaround.

## Live redraw defect resolved (2026-09-14)

The PTY capture exposed a real defect: direct Click stderr diagnostics bypassed the Live console and appended text to its bottom line, moving the cursor beyond Rich's recorded region. Raw frame analysis found an 80-column panel line extended to 128 characters before the next cursor rewind.

Diagnostics during Live now use that same Console; retry/error messages, verbose attempts/phases and block messages are printed above the live region with terminal controls sanitized. Plain/quiet behavior remains unchanged. A regression rejects direct click.echo use while Live is active and verifies literal markup/control sanitization.

Repeated all thirteen actual PTY scenarios after the fix. Exit codes, data counts and degradation assertions passed again. Inspected the updated [terminal reconstruction](terminal-v0.2.0/pty-progress.png): one current progress region, no old progress rows remaining, errors appear above Live at 80/120 columns, and the 40-column activity region retains failure counts and recent events. This resolves the previously recorded redraw concern for these representative scenarios; the image is a monochrome reconstruction rather than a native screenshot. The earlier defective image remains in Git history at 6831676.

## Report metadata and navigation alignment (2026-09-14)

The report now includes a compact metadata table with API, command, software version, start/update UTC timestamps and a relative JSONL link at the top. The complete Logs section links every actual rotation part using URL-encoded relative paths. The rotation regression now resolves each Markdown link and checks every log file is represented, rather than checking plain absolute path strings.

Execution summaries disclose total/data/calendar HTTP attempts separately from logical blocks. Time-range update plans include the latest local active date, and dry-run reports explicitly say Plan only. The six-mode comparison continues comparing all business fields while excluding the newly introduced run-specific timestamps and log link, as permitted by the design.

## Failure threshold and snapshot validation results (2026-09-14)

- E02 now has direct integration assertions for reaching the consecutive-failure threshold, disabling it with zero, resetting the streak after success, and retaining a prior committed block when threshold one stops the run. All assert success/failed/unattempted counts and PostgreSQL rows.
- E03/F07: snapshot scope mismatch, aggregate buffer overflow and cross-status key conflict now mark the responsible subrequest Failed rather than leaving it Received. The actual received-row count is preserved; later statuses are not requested, and retrieve raises before any snapshot merge. Tests verify each error category and the exact requested status prefix.
- Full unit/integration regression: 176 passed in 6.31 seconds; Ruff check passed. These tests add bounded failure evidence without adding task or retry-management features.
