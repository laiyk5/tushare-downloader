# v0.2.0 acceptance and release record

Decision date: 2026-09-15 (Asia/Shanghai). **All 65 v0.2.0 acceptance clauses passed.**

| Item | Accepted state |
| --- | --- |
| Software | v0.2.0; `dceeb299199f2759424b4c4e5b61f35c00b3aeb3` |
| Reviewed candidate | `6d63203667567daac26b14a4c63065edcfa97bd7`; identical tree to the merge |
| Design | `design-v0.2.0`; `248bd3cee2447cea38866dc2c796b31eaf35c34e` |
| Implementation PR | [PR #3](https://github.com/laiyk5/tushare-downloader/pull/3), merged normally after checks passed |
| Checklist | [65-clause signoff](acceptance-index-v0.2.0.md) |
| Detailed evidence | [Execution record](acceptance-v0.2.0.md) |

## Verification

- Local full regression: 191 unit/PostgreSQL integration tests passed; Ruff check and format passed. Branch coverage 93%, used to inspect gaps rather than impose a release threshold. WSL Ubuntu 24.04/Python 3.12.3 connected to an isolated Windows PostgreSQL 18 instance.
- [Candidate Checks](https://github.com/laiyk5/tushare-downloader/actions/runs/34865543484) and [candidate Documentation](https://github.com/laiyk5/tushare-downloader/actions/runs/34865543565) passed. PR deploy was skipped. The current main protection requires `docs-build` from GitHub Actions; no protection was bypassed.
- [Main Checks](https://github.com/laiyk5/tushare-downloader/actions/runs/34865968005) passed code/coverage/build/isolated wheel checks and the PostgreSQL integration suite.
- [Main Documentation and Pages](https://github.com/laiyk5/tushare-downloader/actions/runs/34865968050) passed strict build, Demo and notice verification, uploaded the site artifact, checked main SHA, downloaded that same artifact and deployed it successfully.
- [58 online page/resource checks](pages-v0.2.0.json) returned HTTP 200. Static assets and third-party notice bytes matched the local build. The project subpath is `https://laiyk5.github.io/tushare-downloader/`.
- Browser search for `Trading-day filtering` returned four results including the user download guide. The embedded Demo switched all six Rich/plain × normal/quiet/verbose combinations, preserved report paths, and played from 0/10 to Completed. Its standalone page opened; a 390×844 viewport displayed the partial-failure summary and row table without horizontal clipping. The page provides a static fallback and accurately labels the Demo as simulated. Real terminal evidence is separate under [PTY results](terminal-v0.2.0/summary.json).
- Full supplier notices and runtime artifact boundaries are documented in [licensing](licensing.md). Project MIT does not grant Tushare data redistribution rights.

## Deployment guard and rollback evidence reuse

Compared `.github/workflows/docs.yml` with v0.1.0: v0.2.0 adds build-time Demo/notice/page checks, while the `needs: build` deployment gate, PR prohibition, same-artifact transfer, main-SHA guard and non-cancelled serialized main deployment remain unchanged. A failed build cannot satisfy the deployment dependency. The previous real revert rehearsal remains applicable: commit 65acefa deployed a visible marker ([run 34772567209](https://github.com/laiyk5/tushare-downloader/actions/runs/34772567209)); cb0eb09 reverted it and the redeployed marker disappeared, as recorded in [v0.1.0 evidence](acceptance.md). No deliberately broken content was published for this release.

## Supported scope and limits

Supports daily_basic and stock_basic; no arbitrary API forwarding, task manager or resume service. Successful protocol responses do not prove source business completeness. Calendar filtering is an optimization with an explicit user bypass. Entirely empty snapshots retain old rows; commit acknowledgement loss remains unknown and is not blindly replayed. ETA is an estimate. Logs retain rotated parts but single-file tail does not follow new parts automatically. Excel is an optional downstream example, not an acceptance gate.

Backup/restore, v0.1.0 upgrade, real API and benchmark evidence retain their measured revisions and scope. Later changes affected reporting, tests and documentation; current regression and post-fix output benchmarks cover those changes. Historical results are not presented as fresh timing measurements.

The disposable test database data directory has been removed and its identified test server stopped. The Windows server.log file alone remains locked by an unidentified handle; it is a disposable local artifact, not a repository or database dependency. Production database processes were not stopped.

Software and design versions are independent. Existing tags were not rewritten; this acceptance decision does not require or create a new software tag. Follow-up edits that publish this record only do not alter the accepted application revision.
