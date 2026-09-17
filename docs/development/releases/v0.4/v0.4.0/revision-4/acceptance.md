# Revision 4 acceptance evidence

Status: **automated checks passed; maintainer accepted delivery; unperformed checks are not claimed as passes**.
Design baseline: `design-v0.4.0-r4`, commit `cd39264`.
Current complete run: [626 passed in 196.24s](regression.txt).

## Deterministic cases

The names below refer to tests in `tests/unit/test_setup_dialogue.py` unless specified.
No historical widget pass is used as evidence for the new dialogue.

| Case | Status | Primary evidence |
| --- | --- | --- |
| R4-C01 | Pass | `test_edited_target_is_used_by_check_apply_and_verify`, `test_explicit_edit_beats_environment_and_discards_old_password` |
| R4-C02 | Pass | `test_new_connection_destination_and_secret_isolation`; actual adapter/headless cluster equivalence |
| R4-C03 | Pass | Destination/isolation and separate-save tests; retained setup file concurrency tests |
| R4-C04 | Pass | Destination test (missing explicit path); `test_explicit_missing_config_is_input_error` in headless tests |
| R4-C05 | Pass | `test_ready_full_environment_does_not_create_file`; retained configuration and missing-key tests |
| R4-C06 | Pass | `test_bad_explicit_config_is_not_silently_ignored` |
| R4-C07 | Pass | Ready/error status, exact confirmation, headless final-event tests; service lock/partial-failure tests |
| R4-C08 | Pass (automated); PTY echo evidence pending (agent-owned) | EOF and interrupt tests, verification-only recovery; retained bounded real database cancellation tests |
| R4-C09 | Pass | Separate-save and save-failure tests; `test_writer_credential_edit_requires_save_decision` |
| R4-C10 | Pass | Source boundary below and current complete regression; evidence gaps explicitly retained |

## Requirement disposition

Grouped rows enumerate every effective setup requirement. Pass means the applicable
automated contract is covered; specific missing terminal evidence remains Not run; no user checklist is required.

| Requirements | Status | Evidence |
| --- | --- | --- |
| DBW01, DBW13, DBW14, DBW15, DBW19, DBW20, DBW21, DBW23 | Pass | Current dialogue cases above; shared config/file tests; real adapter equivalence |
| DBW02, DBW03, DBW04, DBW05, DBW06, DBW08, DBW10, DBW12, DBW16, DBW17, DBW22 | Pass | Retained service/cluster suites rerun in current 626: real SCRAM, role/ACL checks, actual v0.3 database, wrong identity, bounded cancellation and partial commits; dialogue credential/recovery cases |
| DBW07 | Pass | Retained atomic/config concurrency tests plus current separate-save and recovery tests |
| DBW09 | Removed | Removed by design; not counted as passed |
| DBW11, DBW18, UI01, UI03, UI04 | Not run (PTY evidence gap; agent-owned) | Automated branches/widths/cold start/exit tests pass; [terminal checklist](terminal-review.md) records the maintainer decision and the remaining evidence boundary |
| UI02 | Pass | Numbered edit, password matching, invalidation, exact confirmation and save/recovery tests |
| H01, H05 | Pass | Updated mode routing, non-TTY/plain rules and real `test_dialogue_and_headless_share_real_plan_and_repeat_safely` in both orders |
| H02, H03, H04, H06, H07, H08 | Pass | Current retained headless/private credentials/logging/exit/cluster suites; installed command smoke |

## Source and historical evidence boundary

Compared with `2902a35`, setup_db.py, setup_config.py, setup_credentials.py and bounded.py
are unchanged. The sole shared setup_service.py change suppresses intermediate final
session events for the interactive adapter; current dialogue tests assert one final event.
The CLI adapter and cold-start path are newly tested. Textual and widget-only tests are
removed; their safety requirements remain in current adapter/service/cluster tests.
The lockfile removes Textual dependencies. Current retained real DB tests were rerun,
so historical results are not relabelled as results from this candidate.

For unchanged A–N scope, retain the revision 3
[inherited audit](../revision-3/inherited-audit.md) and its cited evidence; this revision
makes no new claim that pending human G05/G09/H01/IN07/SC08 layout reviews passed.
Software release and remote deployment are outside this implementation closure.


## Maintainer decision and responsibility correction

The maintainer accepted revision 4 after reporting no apparent usability issue, then
requested that mechanical acceptance be performed by the agent. No exhaustive human
test execution is inferred. The governing workflow now assigns those checks to the
agent; optional subjective feedback is not a blocking gate. Historical results remain
unchanged. Release and push remain unauthorized.
