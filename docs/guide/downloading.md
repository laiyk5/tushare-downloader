# Download, refresh and update

| Intent | Command | Behaviour |
| --- | --- | --- |
| Fill a date range or snapshot | `fetch` (`f`) | Skip valid successful local request records; request missing or invalid blocks |
| Reconcile source corrections | `refresh` | Request when the last reconciliation is older than `MAX_AGE`; `--max-age 0` forces a request |
| Follow daily data | `update daily_basic` | Re-fetch from the latest local active date minus `LOOKBACK_DAYS - 1` through yesterday in Asia/Shanghai |
| Follow a mutable snapshot | `update stock_basic` | Fetch the full snapshot, merge atomically and mark missing old keys stale |

Date endpoints are inclusive. `daily_basic` normally only adds rows, but can have source corrections. `refresh` provides the historical correction entry point. Having one local row on a date is not sufficient to skip the date.

```bash
tushare-downloader fetch daily_basic -s 2024-01-02 -e 2024-01-31
tushare-downloader refresh daily_basic -s 2024-01-02 -e 2024-01-31 --max-age 7d
tushare-downloader update daily_basic --dry-run
tushare-downloader update daily_basic
tushare-downloader update stock_basic
```

For an empty daily table, first fetch an explicit initial range. Snapshot updates can start with an empty table and reject date arguments. A lookback of 7 starts six days before the latest local date, not six days before today. An old local endpoint can therefore produce a long update range.

## Trading-day filtering

`CALENDAR_FILTER=basic` defaults to excluding Saturdays and Sundays without an external dependency. It does not know weekday holidays. `calendar` uses Tushare `trade_cal` for SSE, including weekday holidays; SSE is the stated proxy for regular A-share trading days. `off` disables filtering.

Filtering is an optimization with possible calendar errors. You can explicitly bypass it:

```bash
# Keep fetch's successful-record skipping, but bypass calendar filtering.
tushare-downloader fetch daily_basic -s 2024-01-01 -e 2024-01-07 --ignore-calendar
# Force reconciliation of the entire range, including normally closed days.
tushare-downloader refresh daily_basic -s 2024-01-01 -e 2024-01-07 --max-age 0 --ignore-calendar
```

`--max-age 0` alone still respects the selected calendar filter. Filtering never creates successful download records or marks existing rows stale. It does not apply to `stock_basic`.

Calendar mode prepares all candidate dates before downloading data. If preparation fails, execution stops without data requests; it never silently switches to basic or off. Missing/expired caches can refresh during real execution. Damaged caches must be removed or explicitly bypassed. Dry-run never calls the API or writes the cache: an insufficient cache produces an incomplete plan and exit code 1.

## Failure and reconciliation

Independent date blocks commit separately. A failure does not undo earlier commits; the report distinguishes failed and unattempted blocks. Rerun fetch for missing ranges, or refresh for historical reconciliation. A repeated update recalculates its range; older failures outside that range need explicit fetch/refresh.

The five required `stock_basic` status requests form one logical snapshot. A failed required request prevents merging the snapshot. Received rows are not independently committed. Lost commit acknowledgement is reported as unknown; the downloader does not claim rollback or blindly replay it.

Empty responses remain unverified and keep existing rows. They use `EMPTY_RECHECK_AGE`, except forced refresh. Successful protocol responses do not establish source completeness. Missing keys are marked stale only by refresh or mutable update in their declared scope; fetch and daily update preserve missing old keys.

## Output and reports

The log path appears first. stdout carries plan/results and report paths; stderr carries activity and diagnostics. Rich/plain controls formatting, while `-q` and `-v` control detail. Neither changes stored results.

Progress completion means blocks were processed, not that all succeeded. Received/staged rows are distinct from committed rows. ETA uses up to 20 completed blocks and starts after at least five samples totaling ten seconds; retries, commit pauses and unusually slow blocks suppress the estimate.

`reports/<run>/report.md` first contains the original plan with no final result. At completion it is atomically replaced with results, attention items, the unchanged original plan and full block details. Terminal truncation never truncates the report. A forced kill or failed final write may leave only the initial plan; this does not mean the process is still running or that no data committed.

```bash
# Use the actual log path printed by the downloader.
LOG_FILE='./logs/REPLACE_WITH_RUN_ID.jsonl'
tail -n 20 -f "$LOG_FILE"
jq -c 'select(.event == "slice_result")' "$LOG_FILE"
```

Logs rotate at 10 MiB. Every part is retained and listed in the report. Following one file does not automatically follow newly named parts; inspect all parts for a complete history. See [exit codes](../reference/cli.md).
