# Revision 5 evidence mapping

This mapping distinguishes functional evidence from the recorded execution-budget failure.
It does not turn historical results or unexecuted checks into current passes.

| Requirement | Evidence |
| --- | --- |
| AC01 / AC02 / AC13 | test_suspension_v2, current same-event integration conflict test; five dates, S/R, duplicate fold, timing conflict, NULL/blank/unknown type |
| AC03 / AC09 | test_suspension_migration; actual-v0.3 cluster migration; reader ownership rejection; unchanged rows/OID/view/identity and rollback |
| AC04 | retained old slice records and mismatched spec; actual old software rejects migrated structure; Inspect installed/expected tests |
| AC05 | parent real CLI/API/DB equality and S/R assertions completed before harness Inspect failure; see index execution boundary |
| AC06 | Functional fixed-date results observed; **request budget failed** due to harness process entry. Deviation recorded and explicitly accepted by the maintainer on 2026-09-17; no additional live run |
| AC07 | parent repeated fetch asserted zero HTTP; forced refresh matched fresh source; deterministic reconciliation tests |
| AC08 | preview, explicit confirmation/missing/wrong name and offline local migration tests |
| AC10 | actual old baseline and backup/restore, metadata failure rollback, real COMMIT followed by injected acknowledgement loss, safe preview after |
| AC11 | advisory writer lock; real DDL wait; configured statement budget; interrupt exits 130 |
| AC12 | setup service zero actions/exit 4, actual cluster old facts; init-db/download use validated Store version gate; Inspect old/expected/unknown rules |
| IN07 / IN08 | default overview vs detail; six mode tests; 40 Rich / 80 plain / 120 Rich representative output; existing inspection permissions/budget suites |
| Packaging/docs | wheel/sdist and installed command checks; strict Zensical, aliases/links; source fingerprint at closeout |

Mechanical validation is agent-owned. No new human test checklist is introduced. The
maintainer explicitly accepted this revision's documented budget deviation on 2026-09-17
(“接受偏差，按现有证据验收”). Functional acceptance is complete; the budget failure remains
recorded, not relabelled as a pass. Production migration remains an explicit user operation.
