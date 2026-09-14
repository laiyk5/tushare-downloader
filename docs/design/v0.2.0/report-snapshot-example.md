# stock_basic · update

**Completed** · Illustrative report, not an actual download.

| Context | Value |
| --- | --- |
| Command | `tushare-downloader update stock_basic` |
| Software / report design | 0.2.0 / v0.2.0-draft.4 |
| Scope | Full snapshot |
| Log | `logs/<run>.jsonl` (relative to invocation working directory) |
| Started / finished | 2026-09-14T06:51:00Z / 2026-09-14T06:51:10Z |
| Elapsed / exit code | 10s / 0 |

## Result

**1/1 logical block succeeded (100%)**. HTTP attempts: 5; retries: 0.
All required status requests succeeded. Snapshot merged in one transaction.

| Committed input rows | Inserted | Updated | Unchanged | Reactivated |
| ---: | ---: | ---: | ---: | ---: |
| 5,920 | 20 (0.3%) | 30 (0.5%) | 5,860 (99.0%) | 10 (0.2%) |

Four mutually exclusive categories; shares use 5,920 committed input rows.
Newly stale: **21 / 5,911 (0.4%)** of active rows before reconciliation.

| Local table | Before | After |
| --- | ---: | ---: |
| Active | 5,911 | 5,920 |
| Stale | 12 | 23 |

Missing rows were marked stale, not deleted. Reappearing rows were reactivated.

## Original plan

| Item | Before execution |
| --- | --- |
| Scope | Full snapshot |
| Plan | 1 block requested; 0 skipped |
| Reason | update always requests the full snapshot |
| Write policy | Upsert and reconcile missing keys after all required requests succeed |

## Block details

| Scope | Plan | Outcome | HTTP attempts | Committed input rows |
| --- | --- | --- | ---: | ---: |
| Full snapshot | Request | Non-empty, committed | 5 | 5,920 |

### Required requests

| Filter | Outcome | Attempts | Received rows |
| --- | --- | ---: | ---: |
| list_status=L | Success | 1 | 5,800 |
| list_status=D | Success | 1 | 100 |
| list_status=P | Success | 1 | 20 |
| list_status=G | Success, empty | 1 | 0 |
| list_status=UN | Success, empty | 1 | 0 |

These are components of one snapshot, not independent commits.
Empty G/UN responses do not make the aggregate snapshot empty. Duplicate rows: 0.
