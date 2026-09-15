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

The [design](../design/index.md) and [backlog](backlog/index.md) are maintained in Chinese.
User documentation describes implemented behavior. Design status and implementation/release status are distinct; follow the current [workflow](../design/workflow.md) for the proposed shared delivery version and design revisions.

## Planned database setup work

BL-018 is a draft, not an implemented command. Review the [wizard design](../design/database-setup.md) and DBW acceptance conditions before coding; implementation starts only after design finalization.

Keep prompting separate from connection inspection, plan calculation, execution and verification. Reuse storage initialization and schema validation instead of copying DDL into a CLI or SQL exporter. Keep plans in memory; do not add a task database or resume mechanism.

Role/database creation needs a disposable PostgreSQL 18 cluster, not merely another database on a shared production server: roles are cluster-wide. Use only synthetic credentials and objects. Document the exact local cluster endpoint and owned test objects before tests run. Do not give the normal integration fixture administrator access or reuse the downloader's .env. No new runtime dependency is required by the design.

Implement in dependency order: inspection/no-change path, configuration writing, confirmed creation/grants, then script export. Each step needs contract-based failing tests first. Keep manual setup and init-db usable throughout; add user-facing setup instructions only when the command works and has been verified. Local validation does not authorize GitHub runs or a release.
