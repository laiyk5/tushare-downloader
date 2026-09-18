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
| contracts.py / inspection.py / read_output.py | Shipped contracts, bounded read-only observations and query rendering |
| setup_config.py / setup_db.py / setup_service.py / setup_dialogue.py | Private configuration writes, inspected plans, execution and sequential interactive prompts |
| bounded.py | Short-lived child calls with client deadlines; no persistent service |

The [design](../design/index.md) and [backlog](backlog/index.md) are maintained in Chinese.
User documentation describes implemented behavior. Design status and implementation/release status are distinct; follow the current [workflow](../design/workflow.md) for the proposed shared delivery version and design revisions.

## Database setup implementation

Setup uses the finalized revision 7 output contract on top of revision 6 ordered migrations.
Keep input adapters separate from shared inspection, execution and verification. Tests use
disposable isolated PostgreSQL databases; temporary administrator credentials never enter logs.
The current implementation/verification status is recorded in the versioned release directory.
No change to candidate code authorizes production access or remote publishing.

## Development and production database policy

Use a reusable, resettable `tushare_dev` database on the isolated development PostgreSQL service (currently port 55434; 55433 was unavailable during revision 6 verification), with private `.env.dev` settings. Its host and credentials must be verified from the development service. Revision 6 created it, verified one reset/rebuild, and leaves it ready for development. Automated tests continue to use separate disposable databases and `TEST_DATABASE_URL`.

Candidate code must not access production, including read-only inspection. Production is used only through officially released code; an accepted candidate or local commit is not a release. This is a development convention, not a product-enforced database-name restriction.

Use explicit `-c .env.dev`, and verify the effective server, port, database, account and application database ID before operations: inherited PG* variables override the file. Before resetting, verify the exact isolated target, preserve required evidence and ensure nobody is using it. Never clear a shared cluster, shared roles or other test databases. Keep credentials out of Git.

The setup migration integration is described in the [revision 6 design](../design/database-migrations.md). User-facing command documentation follows the implemented candidate; publication remains a separate step.
