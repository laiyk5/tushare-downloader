# A short user experience session

Use this reference to explore the v0.4.0 candidate as a user: discover the commands, connect
to your local data, download a small sample and understand the result. This is a flexible
experience session, not another acceptance checklist. Completed explorations are recorded separately in [three session reports](user-experience/index.md).

## Agree the limits before starting

- **20 minutes total**, including reading, waiting and troubleshooting. Stop sooner if useful feedback is already clear.
- **At most 25 downloader invocations**, including help, invalid commands, retries and repeats. Unused commands need not be spent.
- **At most two live download invocations and four HTTP attempts in total**, counting failed attempts and retries. Use only `daily_basic` for the single date **2026-01-05**, with `MAX_ATTEMPTS=2` and `CALENDAR_FILTER=basic`. Other download commands stay in dry-run mode. A missing token or API permission is a finding, not a reason to extend the session.
- Use the verified, resettable **tushare_dev** database and `.env.dev`. Candidate code must not connect to production. Do not reset databases, change roles or apply migrations in this session; a setup proposal can be reviewed and declined.
- At either time or command limit, stop issuing commands. Interrupt active work with Ctrl+C and allow cleanup; record any overrun rather than silently extending the budget. Do not start a replacement run.

Before connecting, confirm that inherited PG* settings do not override the intended development
host, port (currently 55434), database and writer. If that cannot be established, stay with offline
help/schema commands. Keep credentials private. This preparation is part of the time budget.
For the bounded live requests, set these non-secret overrides in the session shell:

```bash
export MAX_ATTEMPTS=2 CALENDAR_FILTER=basic
```

## Choose a route; change it as you learn

The following is a menu, not a required sequence. All examples run from the project directory.
Every invocation, including a replacement command, consumes one of the 25 slots.

| Direction | Example | What to notice |
| --- | --- | --- |
| Find your way | `uv run tushare-downloader --help` | Can you find the right command without reading the design? |
| Discover datasets | `uv run tushare-downloader list` | Is the supported data and its purpose understandable? |
| Check setup | `uv run tushare-downloader -c .env.dev setup` | Are the target, current state and next action clear? Exit without applying changes. |
| Look at local data | `uv run tushare-downloader -c .env.dev inspect` | Can you distinguish ready, empty, missing and outdated data? |
| Understand one dataset | `uv run tushare-downloader schema daily_basic` | Can you identify dates, keys and fields you would read? |
| Preview a download | `uv run tushare-downloader -c .env.dev fetch daily_basic -s 2026-01-05 -e 2026-01-05 --dry-run` | Can you tell what will be requested or skipped, and why? |
| Try the real operation | Run the previous command without `--dry-run` | Are the log path, activity, result and next action useful? |
| Repeat or compare | Repeat that same one-day fetch, or use `--plain` before the command | Does the explanation of skipping/rechecking and the output make sense? |

A repeat is the **second** live invocation, even if it is expected to skip. Do not run both a
repeat and a further live comparison. If existing observations skip both requests, accept that
experience; do not clear data or expand the date range merely to force activity. Read the printed
report/log paths within the remaining time. One date may finish without meaningful progress or ETA;
that is not a defect and is not a reason to enlarge this session.

Prefer directions that answer your current question. For example, spend more time on setup if
connection wording is confusing, or use the remaining slots on `inspect daily_basic` and its help.
Do not run an unrestricted `update`: a lagging local endpoint can request a much larger range.
The limits and environment boundary stay fixed even when the route changes.

## Leave a short note

Record elapsed time, downloader invocation count, observed HTTP attempts (or **unknown**),
and whether any data was written. Then note: **what felt easy; where you hesitated; the one change
that would help most**. For a problem, retain the command, expected/actual behavior and redacted
log path. Do not turn this session into debugging or automatically add release gates.
