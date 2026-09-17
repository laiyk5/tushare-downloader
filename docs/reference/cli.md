# CLI reference

```bash
tushare-downloader [OPTIONS] COMMAND [ARGS]...
tushare-downloader --help
tushare-downloader refresh --help
```

## Global options

| Option | Meaning |
| --- | --- |
| `-c, --env-file FILE` | Use this dotenv file instead of cwd/.env |
| `-q, --quiet` | Essential output; does not hide help, list, dry-run or cleanup preview |
| `-v, --verbose` | Request and diagnostic details; mutually exclusive with -q |
| `--plain` | Plain text without terminal control sequences |
| `--version` | Show software version |
| `-h, --help` | Static help; no database or credentials needed |

Place global options before the command. Persistent preferences belong in [configuration](../guide/configuration.md). JSONL files provide machine-readable events; there is no separate JSON terminal mode.

## Commands

| Command | Alias | Options |
| --- | --- | --- |
| `list` | `ls` | List supported datasets offline |
| `init-db` | `init` | Initialize or validate managed objects |
| `fetch API` | `f` | `-s/--start`, `-e/--end`, `--dry-run`, `--ignore-calendar` |
| `refresh API` | — | Fetch range options plus `--max-age DURATION` |
| `update API` | `u` | `--dry-run`, `--ignore-calendar`; no dates or max-age |
| `clean API` | — | `--apply`, `--confirm-database`, `--confirm-database-id` |

APIs: `daily_basic`, `stock_basic`, `daily`, `adj_factor`, `stk_limit` and `suspend_d`. Dates use YYYY-MM-DD. Time-range fetch/refresh require both inclusive endpoints; snapshots reject dates. Durations use units such as 12h/7d, or 0 for forced refresh. Calendar filtering still applies unless explicitly bypassed.

`clean` defaults to preview. Deletion requires both database name and UUID confirmation; see [database operations](../operations/database.md). No abbreviated executable or fuzzy command matching is provided.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | No execution failure; empty responses may still need review |
| 1 | Preparation or execution failure, unattempted blocks, unknown commit or output I/O failure |
| 2 | Invalid arguments or configuration |
| 3 | Another writer holds the database lock |
| 130 | User interruption |

There are no status/resume commands or background task management. See the [download guide](../guide/downloading.md) for rerun behaviour.

## Local data tools

| Command | Purpose |
| --- | --- |
| `schema [API]` | Offline shipped table contracts; no database or token |
| `inspect [API]` / `i [API]` | Five-column local summary by default; one dataset gives full details |
| `inspect API --counts` / `-c` | Also perform exact active/stale row counts for one dataset |
| `setup` | Interactive database setup; `--headless` checks and `--headless --apply` applies necessary changes |

Global options precede the subcommand. Query commands preserve their requested output in quiet mode;
plain mode removes terminal styling. Interactive setup uses sequential prompts, supports --plain and --new, and requires a terminal and explicit confirmation
before database/configuration changes; `setup --headless` supports scripts. Setup additionally
uses exit codes 4 (configuration/changes required) and 5 (unsupported target); see its guide. See [setup](../guide/database-setup.md) and [reading data](../guide/reading-data.md).


Inspect distinguishes installed table structure from recorded request history.
If observations were produced under incompatible request specs, it retains their
timestamps and displays a warning in normal and quiet output. Those historical
times do not establish successful downloads under the current request spec.
Ctrl+C stops inspection with exit code 130; datasets already printed remain visible.


## Explicit schema migration

`migrate suspend_d` previews the supported spec 1 → 2 migration without changing the database.
Apply using `migrate suspend_d --apply --confirm-database NAME` after backup and review.
See [Upgrade suspend_d](../guide/migrate-suspend-d.md). Setup (including headless apply)
reports Migration needed and exits 4; it never implicitly applies this migration.
Inspect shows installed/expected contracts and exits 1 for Migration needed.

Inspect summary columns are Dataset, State, Size, Latest data and Last fetched (UTC).
Size includes indexes and stale rows; last fetched includes successful empty responses.
Ready does not imply complete or up-to-date data. Use `inspect API` for versions,
storage breakdown and the last recorded attempt, or `inspect API --counts` for exact counts.
`list` remains offline, including before a database has been configured.
