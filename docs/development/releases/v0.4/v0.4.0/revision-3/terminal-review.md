# Native terminal review

Status: **Not run by a human**. This checklist is evidence collection, not approval.
Use Windows Terminal with WSL. Never enter real credentials for this first route.

## Route A: isolated interface only

Run in Bash inside Windows Terminal + WSL:

```bash
review_dir="$(mktemp -d)"
touch "$review_dir/.env"
(
  cd "$review_dir"
  env -i HOME="$HOME" PATH="$PATH" TERM="${TERM:-xterm-256color}" LANG=C.UTF-8 \
    uv run --project /home/laiyk/projects/tools/tushare-downloader \
    tushare-downloader -c "$review_dir/.env" setup
)
```

The explicit empty file and cleared environment prevent reuse of normal connection
settings. Do not Apply. No database connection is needed for the following checks.

1. Verify startup explains missing configuration rather than connecting automatically.
2. Enter a non-secret marker in Host, navigate fields with Tab/Shift+Tab and click
   another field with the mouse. Confirm both methods work and retain edits.
3. Inspect Connection, Access, Review and Result at 120×30, 80×24 and 40×20.
   Resize while editing; confirm text/focus survives and controls remain reachable.
   Below 40×20, verify Resize required; restore the size and check retained edits.
4. Enter a deliberately invalid port and use Check. Verify the field explanation
   is understandable and editable. Do not replace it with production credentials.
5. Enter a dummy password marker and verify it is masked. Press Enter while editing:
   it must not authorize database changes. Test Escape from the confirmation dialog
   without losing the draft; then exit with Ctrl+C/confirmation.
6. After exit, type an ordinary shell command. Confirm cursor, echo and colors are
   restored and the final summary accurately says no database changes were applied.

Record terminal/version, tested sizes, keyboard/mouse actions, actual behavior and
any failures. Do not send password values. A successful Route A verifies only the
listed layout/navigation/restoration observations, not DBW11/UI01–UI04 as a whole.

## Remaining human routes

- First successful setup against disposable accounts/database.
- Ready configuration edit and separate file save.
- Partial completion followed by credential correction without replaying writes.
- Long Review differences, long paths, scrolling and accurate retained results.

These routes require a prepared disposable database fixture and separate result
records. Automated cluster tests and browser demos do not sign them off.


## Prepared local routes — 2026-09-17

The current 651-test candidate has a one-time local fixture at
`logs/terminal-review-71816fa2/`. PostgreSQL 18 is already running on isolated port 55433;
its data_directory and the absence of both review targets/roles were verified. This is
not the production port 5432. The helper refuses other database/account targets and
configuration saves outside its private review folder. It clears inherited PG/setup/token
settings before opening the real application. No token or real password is needed.

The fixture is ignored local material, not a new product command. Source/test fingerprints
remain unchanged. Do not change its host/port/account names to production values. If the
server has stopped, report that; do not substitute another connection. Keep the fixture
until results and cleanup are recorded.

### A. First setup, then Ready and configuration saving

In Windows Terminal + WSL:

```bash
cd /home/laiyk/projects/tools/tushare-downloader
uv run --locked python logs/terminal-review-71816fa2/review.py new
```

Keep the supplied host `127.0.0.1`, port `55433`, database
`tdw_review_63da573c_new`, writer/reader names ending `_w`/`_r`.
If prompted for an administrator, use `postgres`, maintenance database `postgres`,
with no password (this isolated cluster uses loopback trust). For newly created writer
and reader passwords use any dummy value, for example `review-only-2026`; confirm it.
Never enter a production password. Review the differences and confirm by typing the
supplied target database name. Expect creation, initialization, grants and access verification.
Then separately confirm saving only the fixture configuration and finish.

Run the same command again. Expect Ready and no database mutations needed. Edit a harmless
connection field, then restore its supplied value, recheck, review and save. Confirm edits
invalidate the earlier check, and that database application and file saving stay separate.
The helper intentionally blocks applying a different target; new-connection visual editing
can be observed without applying, then abandoned.

### B. Partial completion and verification recovery

```bash
uv run --locked python logs/terminal-review-71816fa2/review.py recovery
```

Use the supplied separate target `tdw_review_63da573c_recovery` and its `_w`/`_r` accounts.
Use the same isolated administrator and dummy-password procedure. After actual database
changes and successful real logins, the helper deliberately reports one reader verification
failure. This is a controlled UI fault, not a claim of a genuine password rejection;
real SCRAM rejection is covered by the automated cluster suite.

Expect completed operations to remain visible and configuration not to be falsely saved.
Choose Edit verification credentials, enter the dummy reader password, then Retry access
verification. Expect success without replaying creation/grants. Operation names are recorded
in `recovery-actions.jsonl` for a subsequent independent check; no passwords are recorded.

### Shared visual checks and feedback

During these routes, try 120×30, 80×24 and 40×20; briefly below minimum and back. Check mouse
field selection, Tab/Shift+Tab, text retention across page changes, password masking, long
log paths/review content and scrolling. Enter in a text field must not apply changes.
Cancel a confirmation with Escape; test Ctrl+C/exit and ordinary shell typing afterward.

Also inspect the current offline commands at those widths:

```bash
uv run tushare-downloader --help
uv run tushare-downloader schema daily
uv run tushare-downloader --plain schema daily
```

Report A first setup, A Ready/save and B recovery as pass/fail, plus terminal/version and
any unusable width or control. Do not send passwords. Automated startup/preflight checks
are not human signoff; this page remains Not run by a human until feedback arrives.

After review, the assistant will verify the recorded operations, remove only these two
identified disposable databases/roles and stop the isolated server. No cleanup is done
in this fixture automatically, so evidence remains available for failure investigation.
