# daily_basic · fetch

**Completed with failures** · Illustrative report, not an actual download.

| Context | Value |
| --- | --- |
| Command | `tushare-downloader fetch daily_basic -s 2024-01-01 -e 2024-01-07` |
| Software / report design | 0.2.0 / v0.2.0-draft.3 |
| Started / finished | 2026-09-14T06:51:00Z / 2026-09-14T06:51:30Z |
| Elapsed / exit code | 30s / 1 |
| Log | `logs/<run>.jsonl` (relative to invocation working directory) |

## Result

| Blocks | Non-empty | Empty | Failed | Unknown commit | Not attempted |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 planned | 3 | 1 | 1 | 0 | 2 |

Success: **4/7 (57.1%)**, including empty responses. Failure: **1/7 (14.3%)**.
HTTP attempts: **8 data + 0 calendar** (including 3 retries).

| Committed input rows | Inserted | Updated | Unchanged |
| ---: | ---: | ---: | ---: |
| 300 | 100 (33.3%) | 50 (16.7%) | 150 (50.0%) |

Shares use 300 committed input rows. Reactivated: 0. Newly stale: 0.

## Needs attention

Successful blocks remain committed. Rerun the same command to retry failed or unattempted blocks.
Empty responses follow the configured recheck age; use refresh if an immediate recheck is needed.

| Scope | Outcome | Reason |
| --- | --- | --- |
| 2024-01-01 | Failed | Network timeout; 4 attempts exhausted |
| 2024-01-06 to 2024-01-07 | Not attempted | Execution stopped after a runtime failure; inspect log |
| 2024-01-05 | Empty | Request succeeded with no rows; verify if unexpected |

## Original plan

| Item | Before execution |
| --- | --- |
| Requested / effective range | 2024-01-01 to 2024-01-07 |
| Local table | 500 active rows; 0 stale |
| Range blocks | 7 total = 7 planned + 0 locally skipped + 0 calendar-filtered |
| Calendar policy | off |
| Fetch policy | Skip valid successful fetch records; no eligible records in this range |

Local row counts describe the table before execution, not proof of range completeness.

## Block details

| Scope | Plan | Outcome | Attempts | Committed input rows |
| --- | --- | --- | ---: | ---: |
| 2024-01-01 | Request | Failed | 4 | 0 |
| 2024-01-02 | Request | Non-empty | 1 | 100 |
| 2024-01-03 | Request | Non-empty | 1 | 100 |
| 2024-01-04 | Request | Non-empty | 1 | 100 |
| 2024-01-05 | Request | Empty | 1 | 0 |
| 2024-01-06 | Request | Not attempted | 0 | 0 |
| 2024-01-07 | Request | Not attempted | 0 | 0 |
