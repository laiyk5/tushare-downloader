# Revision 3 acceptance audit

Status: **in progress; not accepted**. This is software evidence, not a change to the finalized design.

`Not run` below means that the complete composite requirement has not yet been verified; it does not
mean that none of its subcases have run. Passing regression counts do not upgrade these statuses.

Evidence checkpoint: 404 unit/integration/cluster tests passed in 33.17s. The real cluster was isolated
by its exact data directory and randomly named fixtures; no production configuration was used.

| Requirement | Status | Scope and remaining evidence |
| --- | --- | --- |
| [DBW01](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW02](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW03](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW04](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW05](../../../../../design/database-setup.md) | Not run | Service failure/cancellation tests pass; each-action real transaction/acknowledgement-loss matrix remains open. |
| [DBW06](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW07](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW08](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW09](../../../../../design/database-setup.md) | Removed | Removed by the finalized revision; not a passing test. |
| [DBW10](../../../../../design/database-setup.md) | Not run | Reader CONNECT repair verified on disposable PostgreSQL; actual v0.3.0 baseline retention evidence still required. |
| [DBW11](../../../../../design/database-setup.md) | Not run | Required Windows Terminal + WSL human routes and terminal restoration not yet signed off. |
| [DBW12](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW13](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW14](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW15](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW16](../../../../../design/database-setup.md) | Not run | Real SCRAM reader empty/wrong/correct password recovery passes; audit all required account paths before sign-off. |
| [DBW17](../../../../../design/database-setup.md) | Not run | Account states and completed operations survive authentication failure; verify full save-failure and subsequent-check history. |
| [DBW18](../../../../../design/database-setup.md) | Not run | Native size/focus tests pass; long-content keyboard/mouse and human routes still need evidence. |
| [DBW19](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW20](../../../../../design/database-setup.md) | Not run | Effective CONNECT and [Ready performance/no-scan evidence](ready-performance.md) pass; audit the remaining classification and credential prompts. |
| [DBW21](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW22](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [DBW23](../../../../../design/database-setup.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI01](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI02](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI03](../../../../../design/database-setup-ui.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [UI04](../../../../../design/database-setup-ui.md) | Not run | Confirmed cancellation now returns 130; complete background failure, terminal restoration and summary coverage remains. |
| [H01](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H02](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H03](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H04](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H05](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H06](../../../../../design/database-setup-headless.md) | Not run | Real SCRAM recovery passes; inspect all pre-write credential cases before marking the composite requirement Pass. |
| [H07](../../../../../design/database-setup-headless.md) | Not run | Map and inspect every subcase against the finalized source before sign-off. |
| [H08](../../../../../design/database-setup-headless.md) | Not run | Unit failure/cancellation cases pass; real per-action fault matrix remains open. |

## Whole-version gates

Inherited acceptance A–J and L–O remain in scope. Release/remote CI is not a local acceptance prerequisite.
Still required: explicit inherited-gate mapping; build/install and headless checks; strict documentation
build and links; old-version retention; native terminal human review.

Relevant current sources include `setup_service.py`, `setup_db.py`, `setup_tui.py`, `setup_config.py`,
`setup_credentials.py`, and their unit/cluster tests. Existing tests must be inspected for scope, not
merely cited by filename. Do not treat the legacy prompt-wizard/export tests as native UI acceptance.
