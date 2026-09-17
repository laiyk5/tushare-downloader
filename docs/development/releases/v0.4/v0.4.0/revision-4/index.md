# Revision 4 implementation

Status: automated implementation checks passed; human terminal acceptance pending. Design: design-v0.4.0-r4 (cd39264).
No release or remote workflow is authorized.

| Scope | Evidence plan |
| --- | --- |
| UI01–04, DBW01/14/15/18/21/23, R4-C01–09 | New sequential adapter and CLI tests; focused first, one stable-candidate regression |
| H01/H05 | Mode validation and shared-service equivalence |
| Remaining DBW/H, data and schema | Reuse revision 3 where source/dependency comparison supports it; rerun affected boundaries only |
| R4-C10 | Explicit source and evidence mapping at candidate closeout |
| Packaging/docs | Remove Textual dependency; build/install and strict documentation checks once stable |
| Human UI | Windows Terminal + WSL, fixed revision 4 minimum routes and widths; pending |

Revision 3 results remain historical. Do not duplicate the database fault matrix for UI-only changes.
The initial revision 4 check is limited to --new routing and interactive plain acceptance.

## Test expectation changes

The first three CLI tests failed because --new was absent and interactive plain was rejected.
After routing changed, Ready/error tests failed before the adapter existed, then passed.
The new adapter's focused configuration, confirmation, verification-only recovery and
separate-save cases pass without touching a real database.

Revision 3 widget tests are retired with setup_tui: focus, modal capture, page layout,
generation races and resize blocking no longer apply. Their configuration/password/confirmation/
partial-result/save requirements map to test_setup_dialogue, shared setup_service/files tests,
fresh-process test_setup_cold_start and the retained real cluster adapter-equivalence test.
No database safety or transaction fault suite was removed. Historical source is available at 2902a35.

## Current focused evidence

- New entry tests: 3 expected failures before routing changed; then passed.
- Sequential adapter: 26 focused cases passed, including explicit connection flow,
  password matching, cancellation, separate save/retry and representative widths.
- Unit checkpoint: 414 passed in 4.35s before the last 7 focused cases were added.
- Real isolated cluster adapter/headless equivalence: 2 passed in 8.46s on port 55433.
- Ruff, wheel/sdist build and isolated package checks passed before final output styling.
- Final complete regression: **626 passed in 196.24s**, no skips; see [output](regression.txt). Human terminal review remains pending.

The only shared-service change is suppression of intermediate session_finished for the
interactive adapter, matching the former TUI handling; one final event is emitted by the adapter.
Database SQL, permission checks, schema and file-atomicity implementation are unchanged.

## Concrete correction trigger (O.4)

The first full regression passed: 624 tests in 204.80s. During the fixed UI03/DBW23
candidate audit, two concrete adapter gaps were reproduced by minimal failing tests:
a changed temporary writer credential did not offer the independent save decision,
and Click's displayed default could emit an embedded terminal escape sequence.
The fixes only mark the writer change for save review and sanitize displayed defaults.
The pre-correction result is retained in regression-before-correction.txt.
Stop condition: these two cases plus the affected adapter suite pass, then one final
stable-candidate full regression. No new platform, scenario matrix or benchmark is added.

[Human terminal checklist](terminal-review.md): prepared, not yet performed.


## Final candidate evidence

- Current unit, integration and real PostgreSQL cluster suites: 626 passed; PostgreSQL 18,
  isolated loopback port 55433, WSL Python. Production database was not used.
- Ruff checks and formatting: passed, 182 files. Installed wheel checks: passed;
  see [installed output](installed-setup.txt).
- Strict Zensical build: passed. Legacy routes: 131; relative links: 8159; broken: 0.
- [Candidate fingerprint](candidate-fingerprint.json) records software/test/lock inputs.
- [Requirement mapping](acceptance.md) separates automated evidence from pending human checks.

The complete regression includes the retained database safety suites. No additional API,
platform or benchmark matrix was added. The two reproduced corrections above are closed.
Unchanged inherited product evidence remains in revision 3; its outstanding human layout
checks are not silently marked passed by this implementation. No remote workflow or release
was performed. Stop automated validation here unless the frozen O.4 trigger occurs.
