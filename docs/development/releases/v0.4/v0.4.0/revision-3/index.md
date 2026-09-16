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


## Authentication recovery and presentation checkpoint

Shared-service and native UI tests now verify that correcting a failed login performs only
read-only access verification. The prior completed operations remain in the result. Replacing the
database identity prevents recovery from being accepted against a different target. Rechecking
the same target with pending authentication routes through verification rather than silently
discarding the previous failure.

A real SCRAM case runs on the disposable cluster. It creates both accounts and the database,
then externally changes the reader's fixture password after grants to reproduce a verification
failure. Empty and incorrect passwords fail; the corrected password succeeds. The mutation list
is unchanged throughout recovery, and fixture passwords are absent from the log. The test scopes
temporary authentication rules to its random roles, checks the exact hba_file/data_directory,
and restores original bytes plus reloads configuration in a finally block.

Full local regression at this checkpoint:
`uv run pytest tests/unit tests/integration tests/cluster -q`: **395 passed in 30.91s**.
This includes the real SCRAM case and ordinary downloader integration tests. A subsequent UI-only
change adds adaptive credential visibility; the native suite passes **13 tests** after that change.
Do not interpret the earlier 395 count as covering the subsequently added case.

Configuration-save previews now show file, current effective/source, selected, saved and resulting
effective values. Passwords are fixed state markers. Tests cover retained old passwords, new files
without saved passwords, environment overrides and matching configurations. Save success and
subsequent event-log failure are distinct outcomes. Wide layouts use a sidebar and side-by-side
connection summary; narrow layouts stack the same controls without recreating inputs.

The browser connector returned `nodeRepl.fetch request failed`; no browser-based visual review was
claimed. Native layout tests pass, but required human Windows Terminal verification remains open.
Further work includes field-local validation, richer database change previews, complete fault and
concurrency matrices, packaging/performance/upgrade evidence and the final requirement-by-requirement audit.


## Field validation, database preview and CONNECT checkpoint

Native setup now validates connection fields before contacting the server. Invalid fields carry
local explanations and focus moves to the first error; editing clears the stale explanation.
Connection parsing lives outside the legacy prompt wizard. Database review now describes each
planned operation with Before / After / Impact and distinguishes an unchanged ready target from
an unavailable plan. Presentation and native interaction tests: **19 passed**.

A real isolated PostgreSQL regression first failed because removing reader CONNECT still produced
an empty plan. Readiness now checks effective database CONNECT together with schema/table/default
permissions. The repaired plan grants only the selected reader and leaves PUBLIC CONNECT revoked.
The regression passed after the fix; no production database was accessed.

Combined local regression after these changes:
`uv run pytest tests/unit tests/integration tests/cluster -q`: **400 passed in 34.27s**.
Ruff and `git diff --check` passed. This is an implementation checkpoint, not acceptance approval.
Remaining work includes per-account failure diagnostics, the complete fault/concurrency matrix,
packaging/performance/upgrade evidence, human terminal verification and the final itemized audit.


## Account verification and cancellation checkpoint

Three test-first cases exposed lost account verification states and an incorrectly successful
partial verification result. Authentication rejection now retains writer/reader states separately;
the service reports failure and permits verification-only recovery. Driver exception text is not
returned. The real SCRAM case explicitly verifies writer=verified and reader=failed after creation.
This does not yet establish per-account progress on a worker timeout or forced cancellation.

A native UI regression first reproduced exit code 0 when the user confirmed cancellation during
execution. It now returns 130 and retains completed/unknown operation lists.

Full local regression: **404 passed in 33.17s**; Ruff and diff whitespace checks passed.
No release or remote workflow was triggered. See the [acceptance audit](acceptance-audit.md) for
the remaining composite requirements; these successful checks do not constitute full acceptance.


## Ready inspection benchmark

[Ready performance and SQL evidence](ready-performance.md) records ten warmed samples each for empty
and 100,000-row datasets. Both p95 values satisfy the 2-second local target; traced inspection does
not scan raw data or change identity/object ownership/ACLs. The complete composite DBW20 gate still
requires its other classification and interaction cases.


## Real transaction fault matrix checkpoint

`test_each_action_preserves_real_transaction_outcomes` passes all ten combinations of five actions
(create writer, create reader, create database, initialize, grants) and two injected faults:

- Real SQL rejection: role creation and grants fail before transaction commit; initialization fails
  inside Store's own transaction after its metadata update and before COMMIT; CREATE DATABASE rejects
  a nonexistent owner before creation. Actual remaining plans prove the rejected action did not persist.
- Lost acknowledgement: the real action commits, then the test drops its successful result. The
  service reports Unknown, retains earlier completed actions, stops later actions and never replays.
  Independent snapshots prove the committed action remains and is absent from the remaining plan.

The initial initialization test incorrectly tried to surround Store's explicit BEGIN/COMMIT with an
outer transaction. Injection was corrected to occur inside the actual transaction; rollback expectations
were retained. This fixture correction is not evidence of a product rollback defect.

A separate test first reproduced an incorrect exit code during pre-write reinspection cancellation.
The service now returns 130 and keeps the action not-attempted, with no writes or unknown commits.

Full local regression: **416 passed in 54.94s**. Ruff and diff checks passed. This matrix does not claim
real socket-loss/worker-kill or per-action deadline coverage; those and the other composite acceptance
requirements remain open. No production database, remote workflow or release was involved.


## Native execution controls and installed package checkpoint

Native modal resize testing confirms that shrinking below 40x20 cannot authorize Apply. A test-first
case exposed password-mode Select and Checkbox widgets remaining editable during execution; they now
lock with Input controls during apply and access verification, and unlock when results arrive.
Native suite: **17 passed**. All unit tests: **304 passed in 6.52s**. These headless Textual tests do
not replace required human terminal experience checks.

`uv build --offline` built both sdist and wheel. The wheel was installed with its dependencies in a
fresh temporary virtual environment, running outside the repository and without PG*/SETUP*/URL
environment configuration. Root help and setup help exited 0; read-only headless with no connection
configuration exited 4; non-TTY interactive setup exited 2. No .env was written, and importing the CLI
did not eagerly import Textual. [Captured outputs](installed-setup.json) are retained.
Reproduce after building with `uv run python scripts/check_installed_setup.py`.

This is installed-package smoke evidence, not full database setup or human acceptance. No remote
workflow or release was triggered. Existing full database regression remains the previous 416-test
checkpoint; this UI-only change was verified with the current unit/native suites.


## Actual old-version baseline

[Actual v0.3.0 compatibility evidence](v030-compatibility.md) verifies old-source initialization,
data/identity/user-view/password retention, grant-only setup and no-op repetition. The isolated test
passed in 2.26 seconds. No structural migration is required for this baseline.


## Startup configuration explanations

Three test-first cases exposed missing DATABASE_URL-only explanations and a missing defensive guard
inside the native application's automatic check. URL-only input now explains that PG* keys are
required without echoing or deleting the URL. Invalid/ambiguous configuration shows its recovery
message and cannot automatically connect, even when candidate values were supplied to the app.
The CLI wrapper already suppressed such auto-checks; the native application now enforces the same
boundary itself. Missing and partial connection configurations receive explicit startup guidance.

Initial widget change events settle before this explanation is displayed. Native/headless focused
suite: **27 passed in 5.41s**. The tests use a forbidden session factory to prove that no automatic
database session is created for ambiguous or URL-only input. Full composite DBW01/DBW19 acceptance
still requires the remaining source/entry combinations and their evidence mapping.


## Log-failure diagnostics checkpoint

A test-first headless case injects a log failure after initialization and on final event emission.
The following grants action is never executed. stderr now contains log_failed, completed initialize
and not-attempted grants; injected private exception text is absent. Previously the service stopped
correctly but its known-result summary was only on stdout, leaving stderr empty.

A second test-first case verifies final-event write failure changes the process result to failure
with reason log_failed while preserving Ready database status and avoiding mutations. This separates
logging failure from database failure. Full unit suite: **309 passed in 6.63s**; Ruff/diff checks pass.
These injected event errors do not replace the remaining real filesystem/close-failure cases or
complete H07/DBW08 sign-off.


## Shared input validation checkpoint

A test-first headless case reproduced multi-host PGHOST reaching session construction even though
native setup rejects it. Headless now uses the same connection_errors validator for host, port,
database/account names, SSL and account separation before creating a session. Invalid inputs return
2 without network access. Full unit suite: **310 passed in 6.77s**; Ruff and diff checks passed.
The forbidden-session test proves early rejection rather than relying on a subsequent connection error.


## Native final-event completeness

A test-first CLI-adapter case exposed omitted readiness and per-account verification fields in the
TUI's session_finished event. Final events now include readiness, reason_code, writer_verification,
reader_verification and configuration alongside operation lists. The restored terminal summary also
prints both account verification states and the log path even when no database session was created.
This verifies serialization and summary behavior with a controlled app result; it is not a substitute
for human terminal restoration testing. Full unit suite: **311 passed in 6.75s**; diff checks passed.


## Real database classification matrix

`test_real_database_classification_never_repairs_unsupported_state` passes six isolated PostgreSQL
scenarios (**6 passed in 5.87s**): writer-owned empty database proposes initialize/grants; other-owner
empty database, unmanaged public table, future schema version, elevated reader and column type drift
are Unsupported with no actions and apply exits 5. A forbidden mutation backend proves the service
never dispatches repairs for those states. Object ownership/ACL snapshots remain equal; external row,
future-version marker and elevated role attribute remain unchanged rather than silently repaired.

Temporary ownership/role changes are confined to random fixture objects and restored before fixture
cleanup. This provides real classification evidence for DBW02/04/22, but does not by itself cover
network/permission Unknown cases, role inheritance or all interactive conflict explanations.


## Inspection conflict explanations

Test-first cases exposed missing reason codes and absent ownership explanations. Inspection now
returns stable reasons for unmanaged objects, owner conflict, incompatible schema, unsafe role
privileges/memberships and unavailable inspection. The reasons survive final results and inspection
events. Native database preview and headless output use fixed English explanations with recovery
guidance; arbitrary backend/driver reason text is not rendered. No automatic ownership change,
revocation or guessed migration was introduced. Full unit suite: **313 passed in 6.78s**.
The preceding real classification matrix validates the states; these tests validate their safe
presentation. Other composite conflict cases and end-to-end acceptance remain under review.


## Writer-only additive initialization and consolidated regression

`test_writer_alone_adds_missing_table_using_existing_reader_defaults` verifies a missing registered
adj_factor table is added using only the ordinary writer identity. No administrator credentials are
supplied; every inspection uses the writer, the only mutation is initialize, and verification is
writer=verified / reader=not_checked. Reader SELECT on the new table is inherited from the existing
default ACL. Database ID and the preexisting daily row remain unchanged. The isolated case passed
in 2.49s.

Consolidated unit/integration/cluster regression after the recent input, diagnostic and UI changes:
**435 passed in 67.25s**. This includes actual v0.3.0 retention, six unsupported-state cases, the
five-action transaction fault matrix, Ready performance, SCRAM and ordinary downloader integration.

Audit updates: DBW06 is supported by actual old-source retention, writer-only addition and refusal
of incompatible structures. DBW12 is supported by the headless fresh-target check/apply/repeat case
and full real setup/reader permissions. DBW22 is supported by old/current compatible software and
future schema/column drift refusal plus safe user-facing diagnostic tests. These bounded approvals
do not approve the remaining composite requirements or the whole release.


## Private credential file acceptance

`tests/unit/test_setup_credentials.py`: **30 passed in 0.31s**. Evidence covers duplicate root and
account fields, unknown keys at each account level, strict object/string/bool/version types, BOM,
invalid JSON, exact 65536/65537 size boundary, group-readable mode, symlink, FIFO, directory and
missing file rejection, and acceptance of an unchanged 0400 file. Marker secrets do not appear in
errors. Invalid sources retain their original bytes.

The owner mismatch test uses the real opened file descriptor metadata with a controlled different
current UID and proves JSON decoding is not reached. It does not claim to have changed OS ownership
or tested Windows ACLs. Code review confirms O_NOFOLLOW/nonblocking open, fstat checks, bounded read,
and no implicit credential-file discovery. A public CLI test with --apply and forbidden session
construction proves invalid credentials exit 2 before log/session creation or database writes.

H02 is marked Pass for the supported WSL/Linux credential-file contract. This does not approve
separate account-isolation, authentication, logfile or human terminal requirements.


## CLI mode boundary acceptance

`tests/unit/test_setup_headless.py`: **23 passed in 0.26s**. The added matrix verifies --apply and
--credentials-file without headless, explicit --plain and configured PLAIN for interactive setup,
and a noninteractive terminal all exit 2 without opening the native app, prompting on EOF, writing
files or starting work. Terminal gating checks both stdin/stdout and TERM=dumb. Root/setup help,
including conflicting execution flags followed by --help, succeeds without configuration/credential
reads even with invalid PGPORT. Existing cases cover valid --plain headless read-only dispatch.

Together with the installed-wheel smoke test, this satisfies H01's CLI boundary requirement.
It does not stand in for interactive terminal usability or backend execution acceptance.


## Account and target isolation

`test_temporary_credentials_preserve_target_and_do_not_cross_accounts` confirms a temporary writer
password changes only the session copy. Host/port/database/writer/SSL remain selected; the admin
inherits the endpoint but gets only its own identity/maintenance database and an empty password when
omitted; reader verification gets only its own identity and no writer password. Original settings
remain unchanged and marker secrets do not enter JSONL.

A test-first worker environment case found PGHOSTADDR was not cleared with the other implicit
identity/target variables. It is now cleared in the spawned worker alongside PGSERVICE, service file,
PGPASSWORD, PGUSER, PGDATABASE, PGHOST, PGPORT and PGSSLMODE. Parent environment is not altered by
production worker isolation. Explicit selected connection fields remain authoritative.

Full unit suite: **342 passed in 6.75s**. Together with writer empty/nonempty precedence tests,
credential target-key rejection, real passwordless setup and SCRAM cases, this supports H03's
identity/source isolation requirement. This does not approve every authentication-failure scenario.
