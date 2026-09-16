# Revision 3 acceptance audit

Status: **in progress; not accepted**. This is software evidence, not a change to the finalized design.

`Not run` below means that the complete composite requirement has not yet been verified; it does not
mean that none of its subcases have run. Passing regression counts do not upgrade these statuses.

Evidence checkpoint: 500 unit/integration/cluster tests passed in 144.72s. The real cluster was isolated
by its exact data directory and randomly named fixtures; no production configuration was used.

| Requirement | Status | Scope and remaining evidence |
| --- | --- | --- |
| [DBW01](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW02](../../../../../design/database-setup.md) | Pass | Real classification matrix covers owned/foreign empty, external objects, managed drift and inspection permission denial; fresh-target headless check proves missing database classification without creation. Missing reader creation is covered by fresh-target/CONNECT/authentication fixtures. Object ACL, schema/function privileges and memberships remain unchanged on refused checks. |
| [DBW03](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW04](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW05](../../../../../design/database-setup.md) | Pass | [Five-action fault matrix](setup-fault-matrix.md): real rollback/commit, pre-execution refusal, bounded timeout/cancel, no replay, fresh-plan completion and Ready no-op. |
| [DBW06](../../../../../design/database-setup.md) | Pass | Actual v0.3.0 retention; test_writer_alone_adds_missing_table_using_existing_reader_defaults; real future-schema/column-drift refusal. See index checkpoints. |
| [DBW07](../../../../../design/database-setup.md) | Pass | test_setup_contracts.py, test_setup_files_r3.py and native save retry: restricted edits, syntax/symlink rejection, optimistic concurrency, private atomic publish, failure preservation and no DB replay. See index evidence. |
| [DBW08](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW09](../../../../../design/database-setup.md) | Removed | Removed by the finalized revision; not a passing test. |
| [DBW10](../../../../../design/database-setup.md) | Pass | [Actual v0.3.0 baseline](v030-compatibility.md): identity/data/view/password retention, grant-only setup, no-op repeat; separate CONNECT repair preserves PUBLIC ACL. |
| [DBW11](../../../../../design/database-setup.md) | Not run | Required Windows Terminal + WSL human routes and terminal restoration not yet signed off. |
| [DBW12](../../../../../design/database-setup.md) | Pass | test_headless_fresh_target_check_apply_and_repeat and test_full_setup_and_reader_permissions: absent accounts/database created from server credentials; real identities and ACLs verified. |
| [DBW13](../../../../../design/database-setup.md) | Pass | Configuration preview tests plus native unchanged-save test: explicit file/environment/input sources, old/new file password behavior, exact no-op save preservation. |
| [DBW14](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW15](../../../../../design/database-setup.md) | Pass | Native matching-password, Keep/Replace/Clear, literal back/quit input and explicit passwordless/conflict tests; field-local error tests. See index checkpoint. |
| [DBW16](../../../../../design/database-setup.md) | Not run | Real SCRAM reader empty/wrong/correct password recovery passes; audit all required account paths before sign-off. |
| [DBW17](../../../../../design/database-setup.md) | Not run | Account states and completed operations survive authentication failure; verify full save-failure and subsequent-check history. |
| [DBW18](../../../../../design/database-setup.md) | Not run | Native size/focus tests pass; long-content keyboard/mouse and human routes still need evidence. |
| [DBW19](../../../../../design/database-setup.md) | Pass | Native startup matrix: absent/token-only/partial PG keys do not connect defaults; URL-only explains unsupported; complete PG values check once; entry adapter proves environment-over-file precedence and file preservation. |
| [DBW20](../../../../../design/database-setup.md) | Not run | Effective CONNECT and [Ready performance/no-scan evidence](ready-performance.md) pass; audit the remaining classification and credential prompts. |
| [DBW21](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW22](../../../../../design/database-setup.md) | Pass | Actual v0.3.0 compatibility needs no migration; real future-schema/column-drift cases refuse changes; safe reason/preview tests explain lack of a supported migration. |
| [DBW23](../../../../../design/database-setup.md) | Pass | Native Ready edit/check/save and environment-override cases plus effective-value preview tests; no database apply required, saved_overridden reported accurately. |
| [UI01](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI02](../../../../../design/database-setup-ui.md) | Pass | Native controlled-delay matrix over eight fields discards stale inspections without losing edited input/focus; resize retains controls/input; closing a pending inspection cancels/discards it, returns 130 and cannot apply. Human terminal restoration remains UI04/DBW11. |
| [UI03](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI04](../../../../../design/database-setup-ui.md) | Not run | Confirmed cancellation now returns 130; complete background failure, terminal restoration and summary coverage remains. |
| [H01](../../../../../design/database-setup-headless.md) | Pass | test_setup_headless.py mode/help/EOF/TTY matrix and installed wheel smoke checks; invalid modes exit 2 before app startup; valid plain headless stays noninteractive. |
| [H02](../../../../../design/database-setup-headless.md) | Pass | test_setup_credentials.py: 30 cases; bounded/type/duplicate/unknown input and file metadata checks; owner mismatch uses controlled UID; public CLI rejects before session creation. See index evidence. |
| [H03](../../../../../design/database-setup-headless.md) | Pass | Temporary credential/target isolation and worker environment tests; credential-file target rejection and writer precedence; real passwordless/SCRAM cases. See index evidence and separate H06 scope. |
| [H04](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H05](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H06](../../../../../design/database-setup-headless.md) | Not run | Real SCRAM recovery passes; inspect all pre-write credential cases before marking the composite requirement Pass. |
| [H07](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H08](../../../../../design/database-setup-headless.md) | Pass | [Five-action fault matrix](setup-fault-matrix.md): real rollback/commit, pre-execution refusal, bounded timeout/cancel, no replay, fresh-plan completion and Ready no-op. |

## Whole-version gates

Inherited acceptance A–J and L–O remain in scope. Release/remote CI is not a local acceptance prerequisite.
Still required: explicit inherited-gate mapping; build/install and headless checks; strict documentation
build and links; remaining unsupported/partial-schema cases; native terminal human review.

Relevant current sources include `setup_service.py`, `setup_db.py`, `setup_tui.py`, `setup_config.py`,
`setup_credentials.py`, and their unit/cluster tests. Existing tests must be inspected for scope, not
merely cited by filename. Do not treat the legacy prompt-wizard/export tests as native UI acceptance.
