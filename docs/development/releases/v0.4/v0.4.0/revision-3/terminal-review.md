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
