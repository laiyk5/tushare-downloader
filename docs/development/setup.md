# Development setup

Check out the project in WSL/Linux. `.python-version` and `uv.lock` pin Python and dependency versions.

```bash
uv sync --locked --all-groups
uv run pre-commit install
uv run pre-commit run --all-files
uv run zensical serve
```

Ruff handles linting and formatting. Pre-commit does not run real API calls or database integration tests.
See [configuration](../guide/configuration.md) for daily use and [quick start](../guide/quickstart.md) for installation and the first download.
Follow [testing](testing.md), [benchmarks](benchmarks.md) and [documentation deployment](documentation.md) for contributor workflows.

## Code map

| Module | Responsibility |
| --- | --- |
| cli.py / config.py | Commands and configuration |
| apis/ | Explicit API fields, keys and behavior declarations |
| planning.py | Date blocks and request selection |
| calendar.py | Optional trading-day filtering and cache |
| client.py | HTTPS, parsing, rate limits and retries |
| storage.py | Managed objects, transactions, merges and observations |
| download.py | Local checks, planning, execution and finalization |
| reporting.py | Terminal progress, Markdown reports and JSONL logs |

The [design](../design/index.md) and [backlog](backlog.md) are maintained in Chinese.
User documentation describes implemented behavior; design versions and software versions are independent.
