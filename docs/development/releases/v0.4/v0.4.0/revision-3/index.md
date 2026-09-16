# v0.4.0 revision 3 implementation record

Status: implementation in progress, **not accepted or released**.

Design baseline: `design-v0.4.0-r3`, commit
`993d14d4f94d9678f6acb0536e8a8cf512693f05`.
The maintainer authorized finalization and implementation, with acceptance as the completion gate.
Implementation results below refer to the uncommitted working tree following that design commit,
not to the clean design commit. No remote workflow or release was triggered.

## Test-first evidence

Observed locally before each corresponding implementation:

| Contract | Initial observation | Current focused result |
| --- | --- | --- |
| H02/H03 private JSON | 16 behavioral failures with importable minimal interfaces; initial missing-module collection error excluded from evidence | 16 passed |
| DBW07/08, H07 files/events | 4 failures, including reproducible overwrite of a concurrently created configuration file | 4 passed |
| DBW06 grants | 2 failures: redundant grants on independent table initialization and grant scope including unknown raw tables | 2 passed |
| DBW03/05, H04–06 orchestration | 6 failures against importable minimal service | 6 passed |
| H01/H04/H07 CLI | 4 failures, 1 already passing; no headless option or read-only entry existed | 5 passed |

Current full unit regression: `uv run pytest tests/unit -q`: **267 passed**.
Ruff passed for the changed modules; final full lint and formatting checks remain part of the delivery gate.
The design build passed strict Zensical checks and 6,843 relative links with zero broken links before tagging.
Textual 8.2.8 is now locked as a runtime dependency.

## Remaining implementation and evidence

- Complete shared service credential/privilege preflight, precise failure/lock/cancellation classification,
  event lifecycle, safe diagnostic explanations and all fault boundaries.
- Verify headless execution against a disposable PostgreSQL cluster, including SCRAM and identity isolation.
- Build and test the native Textual prototype, then integrate Connection / Access / Review / Result;
  preserve focus, dirty generations, credentials and file save decisions, and restore the terminal.
- Remove the superseded interactive/export route from the delivered setup entry and update English guides/help.
- Execute the seven database scenario classes, per-action fault cases, old-library preservation,
  inspection SQL/performance checks, distribution checks, and required real-terminal routes.
- Complete the inherited acceptance requirements; prior revision records do not establish revision 3 acceptance.

No compound DBW/UI/H requirement is marked Pass based only on these narrow unit tests.
All 34 effective requirement indices remain pending full mapped evidence; DBW09 is Removed, not Pass.
Software release remains a separate human decision.

## Native UI and database checkpoint

The native Textual prototype now covers persistent inputs across page changes/resizing,
masked credentials, modal target confirmation, minimum terminal size, and discarding
inspection responses after target edits. Five native UI tests pass; these do not replace
the full integrated UI or required Windows Terminal human acceptance. The production
interactive entry still uses the old implementation until integration is complete.

The service now preflights execution capabilities and existing-account authentication,
distinguishes database rejections from unknown outcomes, and preserves the writer-lock
exit code. An inspection failure after a successful mutation is still classified as
unconfirmed rather than falsely claiming rollback.

Real PostgreSQL testing reproduced and corrected two issues:

- A legitimate writer owning its database was rejected by ordinary-account inspection
  because its implicit pg_database_owner membership was mistaken for an elevated grant.
- Reusing existing accounts for a new database attempted a CONNECT check on the missing
  database during preflight; authentication now uses the maintenance database in that case.

Verified on the disposable PostgreSQL 18.6 cluster at 127.0.0.1:55433, with data_directory
checked against the workspace .tmp-pg-v03/data directory before mutations. The production
5432 instance and production .env were not used. Current combined regression:
`uv run pytest tests/unit tests/cluster -q`: **283 passed in 11.53s**
(276 unit/native-UI and 7 disposable-cluster cases). Cluster configuration also supplied
the explicit psql path for historical export tests, which remain until that obsolete route
is removed. Ruff check passed.

The new real headless case verifies a check creates no database, explicit apply initializes
the full target, repeated apply emits no mutation, configuration bytes remain unchanged,
and marked fixture passwords do not appear in logs. It uses trust authentication and does
not establish the required SCRAM cases. All full acceptance indices remain pending.


## Integrated interactive-entry checkpoint

The production `setup` entry now loads Textual lazily. It no longer calls the old prompt/export
wizard. Headless remains independent, while plain/non-terminal interactive combinations are
rejected. The English setup guide, CLI reference and SETUP_READER_USER template were updated.

Test-first additions observed failures before implementation for confirmed application,
configuration saving without database changes, invalidating credentials after endpoint edits,
new-reader password confirmation, explicit writer-password clearing, interrupting a client wait,
unknown interrupted mutation results, native entry routing and a shared TUI log lifecycle.

Current unit/native UI regression: **286 passed in 4.18s**. Documentation strict build passed;
131 legacy aliases and **6,914 relative links** were checked with no broken links. These counts
refer to the local implementation checkpoint, not final software acceptance.

Implemented interaction now includes confirmed shared-service application, separate configuration
save preview/confirmation, password keep/replace/clear, new-role password matching or explicit
passwordless creation, endpoint credential invalidation, exit confirmation and cancellation.
Client cancellation polls a thread-safe signal and ends its spawned worker without claiming
the server operation rolled back. Completed/unknown/not-attempted categories remain distinct.
TUI rechecks share the log, advance plan_seq, and defer session_finished until the application exits.

### Outstanding audit items

- Complete adaptive credential visibility, actionable field errors, wide/narrow layout and full
  before/after/effective-environment preview, then verify the actual terminal layout.
- Finish authentication-only recovery without replaying creation/grants; preserve prior partial
  outcomes across subsequent checks and accurately summarize save/log failures.
- Exercise cancellation, transaction rejection, lost confirmation, concurrency and log/file failures
  against real PostgreSQL, including SCRAM. Test the final integrated TUI with the same core.
- Check every DBW/UI/H and inherited acceptance item; unit test counts alone are not acceptance.
- Complete packaging, old-version compatibility, SQL-scan/performance evidence, complete regression
  and the required human Windows Terminal routes. No human sign-off has been recorded.
