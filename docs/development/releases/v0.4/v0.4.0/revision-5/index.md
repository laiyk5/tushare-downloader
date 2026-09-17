# Revision 5 implementation

Design baseline: `design-v0.4.0-r5` / `04c495e`. Implementation and verification
are local; no production migration, push or software release is authorized.

## Changes

- suspend_d spec 2 / public schema 2.0.0 uses (ts_code, trade_date, suspend_type).
  Blank types are rejected and same-event conflicting timing still fails atomically.
- Explicit migrate preview/apply preserves rows, table identity and grants. Known old
  structures get a migration instruction; setup does not implicitly migrate.
- Default inspect uses five-column summaries, narrow terminals wrap each logical row;
  one dataset shows details. list remains offline.

## Evidence and bounded corrections

The initial event expectations produced 5 failures and 1 pass; the new key/parser
passed all 6. Migration entry tests failed before the command existed. Setup migration
state and default summary tests also failed before implementation. Historical v1 schema
fixtures remain unchanged; current contract expectations are independently stated.

Focused real database migration tests cover preview/apply/repeat, blank types, confirmation,
foreign keys, retained view/OID/data, transaction rollback, old coverage, locks, log creation,
commit acknowledgement loss and interrupt. The interrupt test exposed exit 1 instead of 130;
that was corrected. Actual v0.3.0 source creates the old database used for migration and
old-software rejection checks. A real pg_dump/pg_restore verifies recovery into a separate DB.

The 40-column summary check exposed interleaved folded columns. The narrow renderer now
wraps logical rows sequentially; the affected 40-case read-command/event suite passes.
The wider complete regression result is recorded separately; source differences and focused
evidence must be read together, rather than claiming every result used an identical tree.

## Real API validation and execution deviation

The parent validation ran the public CLI entry against a dedicated database on port 55433.
Its first fetch requested the fixed 11 dates; immediate repeated fetch made zero requests;
forced refresh requested those 11 dates again. Before starting Inspect, the script asserted
exact equality between distinct raw source rows and active database rows, and at least five
same-stock/day S/R pairs, after both download phases. The subsequent traceback occurred at
the Inspect invocation, after those assertions. This is functional evidence, not a claim
that the entire harness completed successfully. CLI completion summaries are retained in
[live-command-summaries.json](live-command-summaries.json); full authorized data is not published.

**Budget nonconformance:** the original local harness lacked a multiprocessing main guard.
Inspect's spawned workers imported and reran that harness, producing **100 HTTP attempts**
in total instead of the planned normal 22 (and exceeding the worst-case budget 88).
The extra work came from the harness, not the downloader retry policy. The run failed and
is not labelled a clean AC06 process pass. No further API calls were made. The guard was
added; all six leftover databases were individually verified by cluster directory, name,
owner and application identity, then removed. The original parent database had already
been cleaned by its finally block. See [counts](live-event-counts.json) and
[cleanup](isolated-cleanup.json).

Normal executable invocations of inspect and inspect suspend_d then passed, without any
Tushare requests; [summary](inspect-overview.txt) and [detail](inspect-detail.txt) are captured.
These observations preceded the final narrow-layout correction, whose evidence is the
representative width tests. No broadening or retry of the network validation is authorized
by this record. The process deviation remains visible to the maintainer.

## Acceptance decision — 2026-09-17

The maintainer explicitly accepted the recorded deviation: “接受偏差，按现有证据验收”.
Revision 5 is accepted on the existing functional evidence, with the request-budget
nonconformance retained as an accepted deviation. This does not authorize more API
requests, production migration, publishing or a software tag.

Final local evidence:

- [Full regression](regression.txt): 650 passed in 246.20 seconds, before the final narrow-layout correction.
- [Final affected tests](overview-final.txt): 40 passed in 0.32 seconds on the corrected renderer.
- Ruff lint/format and git diff whitespace checks passed.
- Wheel/sdist build and [installed command smoke](installed-setup.txt) passed.
- Strict Zensical build and archive/relative-link checks passed (131 aliases; 8,789 links; no broken links).
- [Candidate fingerprint](candidate-fingerprint.json) identifies the final implementation/test inputs.

No further functional acceptance items remain within revision 5's frozen scope.
