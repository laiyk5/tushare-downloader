# v0.3.0 acceptance and release record

Decision date: 2026-09-15 (Asia/Shanghai). **All 73 acceptance clauses passed.**

| Item | Accepted state |
| --- | --- |
| Software | v0.3.0; `ac39d7f951be86910b8798c27b4ce66eb7835304` |
| Reviewed candidate | `6f236d0f1e818a73e5b7c02e47736577b19c9525`; identical tree to the merge |
| Design | `design-v0.3.0`; `ea630b65c4c99261f3fcf331f3ee2cb800f10d86` |
| Implementation | [PR #5](https://github.com/laiyk5/tushare-downloader/pull/5), merged by the maintainer |
| Checklist | [73-clause signoff](acceptance-index-v0.3.0.md) |
| Evidence | [Execution record](acceptance-v0.3.0.md), [remote checks and maintainer attestation](release-v0.3.0-evidence.json) |

## Verification

- Local full regression: 233 unit and PostgreSQL integration tests passed. Ruff, package build and isolated installation checks passed. Environment: WSL Ubuntu 24.04, Python 3.12.3, isolated Windows PostgreSQL 18.
- Candidate [Checks](https://github.com/laiyk5/tushare-downloader/actions/runs/34949090721) and [Documentation](https://github.com/laiyk5/tushare-downloader/actions/runs/34949090830) passed; PR deployment was skipped.
- [Documentation on main](https://github.com/laiyk5/tushare-downloader/actions/runs/34949870705): success, including docs-build, deploy.
- [Checks on main](https://github.com/laiyk5/tushare-downloader/actions/runs/34949870548): success, including integration, check-ubuntu-latest.
- Public GitHub branch metadata confirms main protection still requires `docs-build`, GitHub Actions app ID 15368. The accepted merge tree equals the checked candidate tree.
- The maintainer confirmed all requested browser checks passed after deployment: navigation, content/images, four added API references, search for `suspend_d`, embedded and standalone demo, mode switching and narrow-window usability. This is human verification reported in the conversation, not an automated browser observation; no screenshot was supplied. Build-time demo checks cover the static fallback links and resources.
- The deployment job used the same build artifact after its main-SHA check. The workflow is unchanged from v0.2.0; build dependency, PR deployment prohibition, serialization and stale-SHA guard retain their earlier verification. The actual revert rehearsal (65acefa → cb0eb09) remains applicable as scoped in the [v0.2.0 record](release-v0.2.0.md#deployment-guard-and-rollback-evidence-reuse).
- Current real API, calendar, backup/restore, terminal and benchmark evidence remains linked from the checklist, with each measurement's original revision and scope preserved.

## Scope and limits

Six APIs: daily_basic, stock_basic, daily, adj_factor, stk_limit and suspend_d. Shared planning, parsing, execution and storage support the A-share daily workflow. Successful responses do not prove source business completeness. Calendar filtering remains optional through explicit bypass. Conflicting same-key suspend_d rows fail the block; empty responses retain existing rows. Commit acknowledgement loss remains unknown. Logs retain rotated parts; single-file tail does not automatically follow new parts. Excel is an optional downstream example.

Code uses MIT; this does not grant redistribution rights to Tushare data. Software and design tags are independent. This signoff does not create a software tag or rewrite existing tags. Follow-up publication of this record changes documentation only, not the accepted application revision.
