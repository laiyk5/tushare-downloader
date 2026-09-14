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
