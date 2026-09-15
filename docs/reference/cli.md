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
| `list` | `ls` | List supported APIs |
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
