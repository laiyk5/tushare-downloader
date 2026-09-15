# v0.4.0 local implementation and acceptance

Candidate: `7a9bc58e074ffef30659af159e3d8557bca6eab2`. Design: `8d5a652f9725f921eab9818fef83f765ab0e29c0` (`design-v0.4.0`, local tag). Software v0.3.0 source: `db806c60eb7d080406aec358a243f331c1f4fc13`. No GitHub workflow, PR, remote push or software release was initiated.

## Implemented scope

| Backlog | Local result | Evidence and remaining boundary |
| --- | --- | --- |
| BL-010 | Passed locally | LG01–LG09: command/alias paths, six output modes, dry-run/non-download behavior, collision/rotation/history retention; existing failure tests cover I/O stop behavior. 35 log-layout tests plus regression. |
| BL-011 | Passed locally | UP01–UP08: actual v0.3.0 source seeded six tables; candidate preserves active/stale rows, identity, observations and ACL; repeated init and reader checks pass. English guide command exercised against isolated database. UP09 is a release gate. |
| BL-014 | Local trial complete | Design commit preceded failure tests, then implementation. Four-state backlog maintained; all development local. Formal software release still requires a human instruction. |
| BL-017 | Implementation and automated checks passed; acceptance pending | DL01–DL04, DL06–DL07 local checks pass; DL05/DL08 browser usability/actual redirect behavior awaits maintainer confirmation. DL09 remains a release gate. |

## Test sequence and corrections

1. Design finalized at `8d5a652f9725f921eab9818fef83f765ab0e29c0` before implementation.
2. Test commit `adfac54` recorded 28 expected failures for missing log-directory and compatibility behavior. Compatibility entry point raised NotImplementedError so failures identified missing behavior rather than an import problem.
3. A new report assertion initially expected absolute paths; existing report contracts use escaped relative links. Corrected the assertion to resolve that established contract, without changing report behavior. Supplemental CLI cases initially used YYYYMMDD; corrected fixtures and the new guide to the existing ISO date syntax. These were test/example mistakes, not weakened product requirements.
4. Runtime implementation `c72e209` passed 274 unit/integration tests with branch coverage 93%. Latest candidate only additionally fixes two benchmark readers to traverse command directories; runtime, tests and dependencies match the tested commit.
5. Output benchmark initially failed because its old flat-directory scan found no final event. Both readers were corrected and their existing request/row/output assertions passed. Output uses 100 rows × 5 days × 5 repetitions per mode; flow uses 10 rows and five repetitions per scenario. These are fake-HTTP, real-test-PostgreSQL measurements, not internet throughput claims.

## Upgrade evidence and reuse limits

The source was extracted from the local v0.3.0 Git tag and imported via an isolated PYTHONPATH; the candidate interpreter used identical installed dependencies. This checks the actual old storage code, not a simulated old API registry or a newly downloaded package. Synthetic rows populate all six tables with active and stale records. Snapshot hash, repeated initialization and reader checks are in local-evidence.json.

Storage, API contracts, configuration loader and dependencies are unchanged from v0.3.0. The existing [restore evidence](../../v0.3/v0.3.0/restore-v0.3.0.json) and [release record](../../v0.3/v0.3.0/release-v0.3.0.md) are reused only for their unchanged restore/data-format and protocol boundaries; this does not claim a fresh real API or restore run. Current regression covers shared behavior. The new directory implementation and changed site require current checks.

## Archive verification

131 artifacts moved into major.minor/patch directories. 124 retain identical bytes; seven Markdown files changed only relative links. The [manifest](../../legacy-paths.json) records before/after hashes and canonical/legacy paths. Zensical normalizes README.md to a directory index; the manifest accounts for that behavior. All 131 aliases exist, attachments match and 4,005 generated relative links resolve. Git attributes preserve raw ANSI bytes. Historical measured values, timestamps and source SHAs were not rewritten.

Strict build, Ruff check/format, Git whitespace check, wheel/sdist isolation and 11 supplier-notice checks passed. Preview is local only. The browser bridge returned nodeRepl.fetch request failed, so actual browser checks are explicitly pending rather than inferred from static HTML.

## Release boundaries

K, UP09 and DL09 are not executed: no request to publish v0.4.0 has been made. Local progress does not trigger remote checks. The implementation is available on the local branch; no software tag has been created. Final browser signoff must be recorded before claiming complete local acceptance of BL-017.

## Navigation correction after maintainer review

The maintainer found that the sidebar remained flat although files had moved. This violated DL08's organization requirement; earlier path/hash checks did not cover navigation hierarchy. Added test_release_navigation.py first and observed its assertion fail because no series groups existed. Corrected Zensical navigation to series → patch → documents, including series and patch overview links. This is an implementation fix under the existing finalized design; no design rule or historical evidence was changed. Browser signoff remains pending until the rebuilt local preview is reviewed.
