# Benchmark guide

Measure network waiting, local processing and database writes separately.
Developer scripts live in benchmarks/; they do not add everyday downloader CLI options.

## Local processing and presentation

```bash
uv run python benchmarks/run.py --mode cpu --rows 1000 --repeat 5
```

No token or database is required. This uses the real parser with fixed HTTP responses and disables network and rate-limit waiting.
Scenarios cover ordinary/duplicate rows; initial fetch, all skipped, failed gaps, partial expiry, forced refresh, update windows and empty responses;
1/7/30-day planning blocks; and plain, progress-off, DEBUG and Rich output.

Planning experiments use pure functions and do not change the daily APIs' one-day request contract.
Presentation measurements use an in-memory terminal (a simulated TTY for Rich) and real file output, not physical terminal rendering.

## PostgreSQL writes

```bash
BENCH_DATABASE_URL='postgresql://tushare_bench:TEST_PASSWORD@localhost:55432/tushare_bench' \
  uv run python benchmarks/run.py --mode database --rows 1000 --repeat 5
```

Both role and database must be named tushare_bench. Missing configuration fails without falling back to the production connection.
The dedicated database is disposable: each repetition clears test data and prepares fixed input outside the measured interval.
Timing includes COPY, merging, metadata writes and COMMIT. Scenarios include insert, unchanged, update, stale, reactivation and empty results.
Unchanged rows still update _last_seen_at and therefore are not zero-write operations.
The example port does not guarantee a running temporary server.

## Small real API sample

```bash
uv run python benchmarks/run.py --mode api --date 2024-01-02 --repeat 5
```

This reads the configured token and requests daily_basic for the specified date without accessing a database.
Rate limits and retries remain enabled; calls consume API quota. Use at least five repetitions.
Access or request failures remain failures rather than being replaced with synthetic results.

## Results and interpretation

Results go to benchmarks/results/UTC-time-random-id/ and are ignored by Git:

- samples.jsonl: raw measurements and per-scenario metrics.
- environment.json: Python, dependencies, platform, CPU count and PostgreSQL version where applicable.
- summary.json and summary.md: sample count, median, minimum, maximum and median absolute deviation (MAD).

Metrics include wall time, peak Python allocations, HTTP attempts, decoded response-body bytes,
HTTP/parsing/rate-limit/retry durations, and planning, deduplication, write or output counts.
HTTP duration includes connecting and reading the body; bytes exclude headers and reflect requests decoding.
Input/database preparation is outside measurement. tracemalloc adds overhead and excludes PostgreSQL memory, OS caches and full-process RSS.

Do not add medians from different layers to estimate end-to-end time or impose fixed performance thresholds across machines.
Real invocation_finished logs also provide phase observations for checks/planning, writes, reports, logs and HTTP processing;
use separately measured wall time for the whole invocation.
Historical [baseline](benchmark-baseline.md) and [output examples](output-examples.md) are retained in Chinese and describe their recorded environments only.

## Complete execution flow

```bash
BENCH_DATABASE_URL='postgresql://tushare_bench:TEST_PASSWORD@localhost:55432/tushare_bench' \
  uv run python benchmarks/flow.py --rows 100 --repeat 5
```

This runs the real executor, parser, PostgreSQL writes and logs/reports with fixed synthetic HTTP responses.
Network and rate-limit waits are explicitly disabled; response and database preparation are outside measurement.
Scenarios cover initial fetch, all skipped, failed gaps, partial expiry, full refresh, append updates, deletion/reactivation,
empty responses, duplicate keys, partial failure and long reports, with at least five repetitions each.
Both role and database must be tushare_bench; production fallback is prohibited.
