# Revision 3 acceptance audit

Status: **in progress; not accepted**. This is software evidence, not a change to the finalized design.

`Not run` below means that the complete composite requirement has not yet been verified; it does not
mean that none of its subcases have run. Passing regression counts do not upgrade these statuses.

Evidence checkpoint: 500 unit/integration/cluster tests passed in 144.72s. The real cluster was isolated
by its exact data directory and randomly named fixtures; no production configuration was used.

| Requirement | Status | Scope and remaining evidence |
| --- | --- | --- |
| [DBW01](../../../../../design/database-setup.md) | Pass | Native absent/ambiguous/partial configuration and field-error tests plus H01 public CLI mode/help matrix: no default connection, existing inputs retained, no help I/O, conflicts exit 2 before UI/session startup. |
| [DBW02](../../../../../design/database-setup.md) | Pass | Real classification matrix covers owned/foreign empty, external objects, managed drift and inspection permission denial; fresh-target headless check proves missing database classification without creation. Missing reader creation is covered by fresh-target/CONNECT/authentication fixtures. Object ACL, schema/function privileges and memberships remain unchanged on refused checks. |
| [DBW03](../../../../../design/database-setup.md) | Pass | Valid-plan cancellation/wrong-name/edited-review native tests dispatch no apply; stale-result matrix invalidates checks; real concurrent-state test refuses an old plan before mutation. |
| [DBW04](../../../../../design/database-setup.md) | Pass | Real creation/reader denial tests, role/membership/unsafe grants classification, database/table/schema ownership rejection, actual-account/database identity checks and SCRAM grant-only repair with preserved password hashes. Writer-only add-table and Ready checks do not require reader login. |
| [DBW05](../../../../../design/database-setup.md) | Pass | [Five-action fault matrix](setup-fault-matrix.md): real rollback/commit, pre-execution refusal, bounded timeout/cancel, no replay, fresh-plan completion and Ready no-op. |
| [DBW06](../../../../../design/database-setup.md) | Pass | Actual v0.3.0 retention; test_writer_alone_adds_missing_table_using_existing_reader_defaults; real future-schema/column-drift refusal. See index checkpoints. |
| [DBW07](../../../../../design/database-setup.md) | Pass | test_setup_contracts.py, test_setup_files_r3.py and native save retry: restricted edits, syntax/symlink rejection, optimistic concurrency, private atomic publish, failure preservation and no DB replay. See index evidence. |
| [DBW08](../../../../../design/database-setup.md) | Pass | Native SVG/page/save-preview marker checks; only opt-in writer secret persists in mode-0600 config; reader/admin never persist; special-character real SCRAM creation/login; identifier validation/driver quoting; H02/H07 private-file, secret-free exception and log-failure evidence. |
| [DBW09](../../../../../design/database-setup.md) | Removed | Removed by the finalized revision; not a passing test. |
| [DBW10](../../../../../design/database-setup.md) | Pass | [Actual v0.3.0 baseline](v030-compatibility.md): identity/data/view/password retention, grant-only setup, no-op repeat; separate CONNECT repair preserves PUBLIC ACL. |
| [DBW11](../../../../../design/database-setup.md) | Not run | Required Windows Terminal + WSL human routes and terminal restoration not yet signed off. |
| [DBW12](../../../../../design/database-setup.md) | Pass | test_headless_fresh_target_check_apply_and_repeat and test_full_setup_and_reader_permissions: absent accounts/database created from server credentials; real identities and ACLs verified. |
| [DBW13](../../../../../design/database-setup.md) | Pass | Configuration preview tests plus native unchanged-save test: explicit file/environment/input sources, old/new file password behavior, exact no-op save preservation. |
| [DBW14](../../../../../design/database-setup.md) | Pass | Eight-field delayed-result matrix and scoped credential invalidation preserve focus/input and prevent stale Apply. Changed save paths independently re-read destination and require file confirmation, as specified in UI section 2; no database recheck is required for save-only preferences. |
| [DBW15](../../../../../design/database-setup.md) | Pass | Native matching-password, Keep/Replace/Clear, literal back/quit input and explicit passwordless/conflict tests; field-local error tests. See index checkpoint. |
| [DBW16](../../../../../design/database-setup.md) | Pass | Real SCRAM covers empty/wrong/correct writer and reader credentials, post-creation read-only recovery, pre-grant refusal, grant-only repair and unchanged existing password hashes. New-role missing/explicit-passwordless choices are covered by shared-service and fresh-target cluster tests. |
| [DBW17](../../../../../design/database-setup.md) | Pass | Real SCRAM partial recovery; per-account worker timeout/cancel preserves verified writer and completed operations; native file-only save retry and replan history retain earlier results; verification-log failure preserves known account states. |
| [DBW18](../../../../../design/database-setup.md) | Not run | Native size/focus tests pass; long-content keyboard/mouse and human routes still need evidence. |
| [DBW19](../../../../../design/database-setup.md) | Pass | Native startup matrix: absent/token-only/partial PG keys do not connect defaults; URL-only explains unsupported; complete PG values check once; entry adapter proves environment-over-file precedence and file preservation. |
| [DBW20](../../../../../design/database-setup.md) | Pass | Real managed database with missing reader plans only create-reader/grants; writer without role-creation privilege is rejected before writes; admin-authorized repair preserves database identity. Combined with real Unknown cases, CONNECT repair, native adaptive credential fields and refreshed Ready no-scan/performance evidence. |
| [DBW21](../../../../../design/database-setup.md) | Pass | Native new-connection matrix over Ready/needs configuration/Unknown/Unsupported preserves original and occupied new files; fresh Ready recheck uses a new session; overwrite refusal preserves destination. Real native/headless parity covers existing Ready target no-op; prior credential-detachment regression covers recovery state. |
| [DBW22](../../../../../design/database-setup.md) | Pass | Actual v0.3.0 compatibility needs no migration; real future-schema/column-drift cases refuse changes; safe reason/preview tests explain lack of a supported migration. |
| [DBW23](../../../../../design/database-setup.md) | Pass | Native Ready edit/check/save and environment-override cases plus effective-value preview tests; no database apply required, saved_overridden reported accurately. |
| [UI01](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI02](../../../../../design/database-setup-ui.md) | Pass | Native controlled-delay matrix over eight fields discards stale inspections without losing edited input/focus; resize retains controls/input; closing a pending inspection cancels/discards it, returns 130 and cannot apply. Human terminal restoration remains UI04/DBW11. |
| [UI03](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI04](../../../../../design/database-setup-ui.md) | Not run | Confirmed cancellation now returns 130; complete background failure, terminal restoration and summary coverage remains. |
| [H01](../../../../../design/database-setup-headless.md) | Pass | test_setup_headless.py mode/help/EOF/TTY matrix and installed wheel smoke checks; invalid modes exit 2 before app startup; valid plain headless stays noninteractive. |
| [H02](../../../../../design/database-setup-headless.md) | Pass | test_setup_credentials.py: 30 cases; bounded/type/duplicate/unknown input and file metadata checks; owner mismatch uses controlled UID; public CLI rejects before session creation. See index evidence. |
| [H03](../../../../../design/database-setup-headless.md) | Pass | Temporary credential/target isolation and worker environment tests; credential-file target rejection and writer precedence; real passwordless/SCRAM cases. See index evidence and separate H06 scope. |
| [H04](../../../../../design/database-setup-headless.md) | Pass | Actual CLI/shared-service matrix compares exit codes, operation lists and final JSONL for Ready, missing reader, Unknown, Unsupported, lock, partial failure and cancellation. Real classification and actual writer-lock cluster tests independently establish database semantics. |
| [H05](../../../../../design/database-setup-headless.md) | Pass | Native Textual and actual headless CLI share a real five-action plan; both execution orders converge to Ready without repeated writes or config changes. Existing real concurrent-state refusal, old-password retention and fresh-plan fault-retry cases cover changed facts/no expansion. |
| [H06](../../../../../design/database-setup-headless.md) | Pass | Real SCRAM covers empty/wrong/correct writer and reader credentials, post-creation read-only recovery, pre-grant refusal, grant-only repair and unchanged existing password hashes. New-role missing/explicit-passwordless choices are covered by shared-service and fresh-target cluster tests. |
| [H07](../../../../../design/database-setup-headless.md) | Pass | Private event schema/mode tests, real unwritable log directory before inspection, injected mid-write/final-event/close failures, marker-secret exclusions and CLI .env byte preservation. Known operation results survive log failures; no subsequent write is dispatched. See index checkpoints. |
| [H08](../../../../../design/database-setup-headless.md) | Pass | [Five-action fault matrix](setup-fault-matrix.md): real rollback/commit, pre-execution refusal, bounded timeout/cancel, no replay, fresh-plan completion and Ready no-op. |

## Whole-version gates

Inherited acceptance A–J and L–O remain in scope. Release/remote CI is not a local acceptance prerequisite.
Still required: explicit inherited-gate mapping; build/install and headless checks; strict documentation
build and links; remaining unsupported/partial-schema cases; native terminal human review.

Relevant current sources include `setup_service.py`, `setup_db.py`, `setup_tui.py`, `setup_config.py`,
`setup_credentials.py`, and their unit/cluster tests. Existing tests must be inspected for scope, not
merely cited by filename. Do not treat the legacy prompt-wizard/export tests as native UI acceptance.
