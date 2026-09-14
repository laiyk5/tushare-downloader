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
