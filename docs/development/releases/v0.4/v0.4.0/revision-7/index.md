# Revision 7 implementation and acceptance

Status: **implemented and accepted locally; v0.4.0 remains unreleased**.
Design baseline: `design-v0.4.0-r7` / `5925e8a`; source inputs are identified by the
[candidate fingerprint](candidate-fingerprint.json). Documentation status-label corrections do
not move the frozen design tag. [Design review](design-review.md) records the prior rationale.

## Delivered

- Preparation errors share safe terminal/report/JSONL descriptions and a single preparation_failed
  event. Missing token has an actionable hint; unknown exceptions do not expose raw messages.
  Calendar attempts and undetermined ranges remain distinct from zero data requests. Empty failure
  block tables are omitted. Existing inner exceptions and exit codes are preserved; sanitization
  applies at the CLI boundary. Completed reports are not processed again as preparation failures.
- Setup explains readiness, untested logins, unchanged settings and unsaved edits without adding
  account checks, writes or new persisted states. Headless explicitly does not save configuration.
- Misplaced recognized global flags get safe placement hints. Legitimate subcommand options keep
  their meaning; unknown spellings and argument groups are not guessed or automatically replayed.
- list/ls show six dataset purposes and daily/snapshot labels, offline in every verbosity mode.
  Main and download help explain that quiet retains explicit queries/previews.
- User guides and developer module references are synchronized. No schema/data/permission migration.

## Verification and correction boundaries

[Test-first output](test-first.txt): **21 failures / 1 pass** against independent desired behavior.
Boundary tests also exposed missing calendar-count fields before correction; their output is
[retained](boundary-before-fix.txt). The initial full-run collection found two new test modules
with the same basename; [collection output](collection-before-fix.txt) is retained. Renaming the
integration module fixed collection before the complete run executed.

[Complete regression](regression.txt): **721 passed / 2 failed in 223.00s**. These were real issues:
preparation wrapping changed an internal error assertion, and a before-report I/O failure tried
to log again after the execution finalizer had already closed the stream. The implementation now
keeps the original exception internally, uses a safe CLI-boundary description, and excludes already
closed reporters from preparation finalization. No failing safety assertion was removed.

[Final affected regression](corrected-affected.txt): **660 unit/integration cases passed in 44.31s**,
including both failed cases and all download/report/CLI boundaries. The **63 cluster cases** passed
in the preceding full run; the final correction changes download Reporter/guarded error handling,
not setup services, database migration or cluster adapters. It adds no behavior to non-Reporter
exceptions. Therefore those cluster results are reused rather than rerun. This is explicitly a
combined evidence decision, not a claim that an identical final tree had a second full run.

Final [build](build.txt), [distribution audit](distribution.txt), [installed setup](installed.txt),
Ruff and strict documentation/link checks passed. One [80-column real PTY Ready sample](terminal-ready.txt)
uses the verified development database, with [result metadata](terminal-ready.json). No database
changes or remote data requests were made by that sample. Text evidence has trailing whitespace
removed for repository hygiene; test outcome content is unchanged.

## UX01–UX07 evidence mapping

| Requirement | Primary evidence |
| --- | --- |
| UX01 | test_preparation_cli: public normal/quiet missing-token and dry-run, real isolated DB zero rows/observations and forbidden HTTP; test_revision7: four log levels and one error event |
| UX02 | test_revision7 safe secret/log/report faults with verbose; existing calendar failure fixture now asserts one event, actual calendar attempts, zero data attempts and retained undetermined scope; output-fault/commit invariants pass in affected regression |
| UX03 | Shared presentation state cases; existing setup dialogue/environment/new-connection/save-recovery tests, with saved/declined output assertions; headless event enums remain unchanged; real PTY Ready sample |
| UX04 | Misplaced plain/short/file/file=value, private value omission, legitimate counts/help, unknown spelling/short group/-- boundary; standard help argument tests retained |
| UX05 | Six descriptions, list/ls, quiet/verbose/plain, representative 40/80/120 widths; ordinary stdout wraps naturally without a separate redraw surface |
| UX06 | Main/fetch/refresh/update help assertions; existing quiet behavior tests retained rather than a new mode matrix |
| UX07 | Topic design and English guides/reference synchronized; strict build, link/alias checks and offline installed help/list checks |

All UX groups have passing final affected evidence or explicitly applicable unchanged evidence.
No Tushare API calls, production access, push, workflow, software tag or release occurred.
The earlier revision 5 request-budget deviation remains historical and unchanged. Remote release
checks still apply when the maintainer requests publication; this record does not claim deployment.
