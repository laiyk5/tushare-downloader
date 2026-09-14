# v0.2.0 implementation and acceptance record

Design: `design-v0.2.0` (`248bd3cee2447cea38866dc2c796b31eaf35c34e`).
Implementation branch: `codex/implement-v0.2.0`. Status: **in progress, not accepted**.
The normative checklist remains [design acceptance](../design/acceptance.md).

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
