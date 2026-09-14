# Configuration

The downloader reads `.env` in the current working directory, or the file selected with `-c FILE`. Environment variables override the file; explicit command options override corresponding settings. Missing settings use defaults. No parent-directory search or dotenv variable interpolation occurs. Relative paths resolve from the working directory, not the configuration file directory. Keys and enumerated values are case-sensitive.

```bash
tushare-downloader -c ./config/local.env --plain fetch stock_basic
```

Keep credentials out of command arguments, logs and Git. Help and list need no token or database. Init, cleanup and dry-run need database access but no token. Real remote requests, including calendar preparation, need a token.

## Complete template

The following template documents defaults, units and valid values. Copy it only when creating a new configuration; retain existing values when upgrading.

```dotenv
# Local configuration. Never commit real credentials.
# Environment variables override this file. Relative paths use the working directory.

# --- Credentials ---
# Required for remote data requests.
TUSHARE_TOKEN=

# --- Database ---
PGHOST=localhost
# TCP port: 1..65535.
PGPORT=5432
PGDATABASE=tushare
PGUSER=tushare_writer
# Supply a password if required by your PostgreSQL authentication setup.
PGPASSWORD=
# disable / allow / prefer / require / verify-ca / verify-full
PGSSLMODE=prefer

# --- Requests & retries ---
# Positive request budget per minute; API-specific limits still apply.
REQUESTS_PER_MINUTE=60
# Total attempts, including the initial request; integer >= 1.
MAX_ATTEMPTS=4
# Seconds; each must be an integer >= 1.
CONNECT_TIMEOUT_SECONDS=10
READ_TIMEOUT_SECONDS=60
RETRY_MAX_SECONDS=60
# Bytes; 33554432 = 32 MiB. Must be positive.
MAX_RESPONSE_BYTES=33554432
# Stop after this many consecutive failed blocks; 0 disables this threshold.
MAX_CONSECUTIVE_FAILED_SLICES=10

# --- Refresh & update ---
# Freshness threshold, e.g. 12h or 7d. Use 0 to force refresh.
MAX_AGE=24h
# Calendar days counted backward from the latest local date, inclusive; integer >= 1.
LOOKBACK_DAYS=7
# Positive duration before rechecking a successful empty response.
EMPTY_RECHECK_AGE=24h

# --- Trading-day filter (v0.2.0) ---
# basic: weekends; calendar: external trading calendar; off: no filtering.
# Calendar preparation failure does not automatically change this choice.
CALENDAR_FILTER=basic
# Used only by calendar mode. Cache contents are disposable.
CALENDAR_CACHE_DIR=./.cache/tushare-downloader/calendar
# Positive duration; used only by calendar mode.
CALENDAR_MAX_AGE=24h

# --- Logs & reports ---
LOG_DIR=./logs
REPORT_DIR=./reports
# File logging: DEBUG / INFO / WARNING / ERROR. Independent of -q/-v.
LOG_LEVEL=INFO

# --- Terminal output ---
# true/false (also accepts 1/0). Unsupported terminals use plain output automatically.
PLAIN=false
# auto / off; off suppresses progress, not warnings or errors.
PROGRESS=auto
# Seconds between static progress updates: 1..60.
PROGRESS_INTERVAL_SECONDS=5
# Rich recent activity entries: 0..20; 0 hides the activity list (v0.2.0).
TERMINAL_LOG_LINES=5
# Maximum summary items per category; integer >= 1. Full reports are not truncated.
REPORT_MAX_ITEMS=20

# --- Development only ---
# Tests and benchmarks read these from the PROCESS ENVIRONMENT, not this dotenv file.
# They never fall back to the production database settings above.
# These commented names are reminders, not active downloader configuration.
# TEST_DATABASE_URL=
# BENCH_DATABASE_URL=
```

## Output and calendar preferences

`--plain`, `PLAIN=true`, `NO_COLOR` or an unsupported terminal select plain output. `-q` and `-v` change terminal detail without changing database results or file logging. `PROGRESS=off` suppresses dynamic and periodic progress, retaining applicable event diagnostics. `TERMINAL_LOG_LINES=0` hides recent activity, not warnings.

`CALENDAR_FILTER=basic` excludes weekends without external data. `calendar` uses cached SSE trading days from Tushare; `off` disables filtering. `--ignore-calendar` bypasses all calendar filtering for one invocation and does not read or refresh the cache. Selected calendar mode never silently falls back; see [download behaviour](downloading.md).

Tests and database benchmarks accept `TEST_DATABASE_URL` and `BENCH_DATABASE_URL` only from their process environment. Setting these in the downloader dotenv file does not configure pytest. They never fall back to production. See [testing](../development/testing.md).
