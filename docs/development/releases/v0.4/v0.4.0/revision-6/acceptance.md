# Revision 6 acceptance mapping

Scope: design acceptance Q, MG01–MG08. Mechanical verification is agent-owned.
This mapping does not replace recorded output or re-label historical evidence.

| Requirement | Primary evidence and boundary |
| --- | --- |
| MG01 | test_migration_planning; setup snapshot/contract/service tests; real setup migration/blocker test. Ready checks remain catalog-only; data preflight is a separate bounded call. |
| MG02 | 13 planner cases: start/intermediate/target, absent dataset, unknown versions, missing edge, cycle, competing successor, dependency order, duplicate IDs. Synthetic versions are not claimed as real releases. |
| MG03 | test_migration_execution plus test_migration_chain real PostgreSQL cases: second-step rollback or actual commit followed by lost acknowledgement, remaining-plan rerun, final no-DDL version step. |
| MG04 | real writer/DDL lock tests, cross-commit writer-lock test, actual statement timeout, bounded event deadline/cancel, changed-plan and setup interruption tests. No extra OS or terminal matrix. |
| MG05 | setup service/headless/dialogue suites; actual_v030 public executable check/missing/wrong/confirmed route; real blank-type blocker; existing config/credential tests reused for unchanged rules. |
| MG06 | actual_v030 source extracted from the real tag, public setup apply, preserved database identity/data/user view/roles and old-software rejection; shared real migration tests cover rows/OID, dependencies, blank types, metadata rollback, old slice retention. Existing reader denial and restore assertions remain. |
| MG07 | terminal-migration.txt + terminal-review.json; 97 final affected tests, headless help/removal/option tests, private logs and failure-boundary tests; installed package smoke and strict docs build. Old migration-guide URL retained. |
| MG08 | development-database.json and create/recreate output; exact isolated cluster/owner/application validation, one reset and unchanged other database OIDs; existing config precedence tests cover PG* override using synthetic values. Private .env.dev is ignored and not committed. No production/API access. |

AC/UP/SC/DBW/H/UI mapping follows design Q.2: storage invariants are tested through the shared
migration core; removed standalone-CLI confirmation/exit tests are replaced by setup tests.
The same old-version fixture covers upgrade and schema requirements, without repeating live API
validation. Revision 5 API evidence remains historical, including its accepted deviation.

MG01–MG08 are accepted on the recorded evidence. The full regression passed 683 tests; the final
output correction and enhanced actual-old-version fixture have their own passing results. Build,
installed entry and strict documentation checks passed. No additional human terminal checklist
or remote publishing gate is required.
