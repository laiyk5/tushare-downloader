# Database setup

PostgreSQL must already be running. Use the interactive setup prompts to inspect a connection,
create the required database and accounts, or complete missing tables and read permissions.

```bash
uv run tushare-downloader setup
uv run tushare-downloader -c ./research.env setup
```

## Interactive setup

Use Windows Terminal with WSL/Linux Python. Setup reads existing configuration and
checks readiness automatically. A ready connection exits immediately without changing anything.

To configure another connection while keeping the old file, run:

    uv run tushare-downloader setup --new

For the same prompts without color or decorative output:

    uv run tushare-downloader --plain setup

1. Enter missing connection information. PostgreSQL must already be running, but the target
   database and accounts do not need to exist. Use temporary administrator access when needed.
2. At a summary, choose **Edit settings** and select a field by number. Other values are retained.
   Changes invalidate the previous check. Passwords are hidden; they have no navigation keywords.
3. Review the target and **Before / After / Impact** for each necessary action. Type the exact
   target database name to apply. Pressing Enter never silently authorizes database changes.
4. Read each completed or failed step. Configuration saving is a separate confirmation.
   Administrator and reader passwords are never saved; saving the writer password is opt-in.

Blue identifies questions and stages, green indicates success, yellow highlights proposed changes
or incomplete results, and red marks errors. Text labels remain sufficient without colors.
Output stays in normal terminal scrollback. Use Ctrl+C to interrupt; there are no full-screen
pages, function-key shortcuts, or minimum-height requirements.

The log path is printed before the first database check. Completed changes remain if a later
step fails. Recheck before retrying; an unknown server outcome is not treated as a rollback.
Authentication recovery verifies access without repeating completed database changes.

At startup, environment variables override file values. Explicit edits in this session take
precedence for the current check and execution. Saving does not change your shell environment:
the preview shows if environment variables will still override the saved settings in later commands.

With --new, old passwords are not inherited. An existing source file is preserved, and a
separate unused .env.new path is suggested. A nonexistent explicitly selected -c path is the
proposed save destination. Saving always requires confirmation. Select a separately saved file
with -c for subsequent commands.

## Headless setup

Scripts prepare the PG* configuration themselves. Checking is read-only by default:

```bash
uv run tushare-downloader -c ./research.env setup --headless
uv run tushare-downloader -c ./research.env setup --headless --apply \
  --credentials-file ./setup.private.json
```

`--apply` authorizes the finite, necessary database changes for the selected target. Headless mode
never asks questions or writes `.env`. It accepts `--plain`; output remains ordinary text.
Choose the reader account with `SETUP_READER_USER` (default `tushare_reader`).

The optional credentials file supplies temporary authentication, not the target connection:

```json
{
  "version": 1,
  "admin": {"user": "postgres", "maintenance_database": "postgres", "password": "REPLACE_ME"},
  "writer": {"password": "REPLACE_ME"},
  "reader": {"password": "REPLACE_ME"}
}
```

Replace the placeholders through your preferred secret-management method. Omit unneeded accounts.
The file must be a UTF-8 regular file owned by the current WSL/Linux user, at most 65,536 bytes,
with no group or other-user permissions. Symbolic links, duplicate keys and unknown fields are rejected.

```bash
chmod 600 ./setup.private.json
```

A temporary writer password overrides `PGPASSWORD` for this invocation only; an omitted or empty
temporary password preserves the configured authentication. Passwords are not accepted as CLI
arguments. For a new passwordless account, use `"allow_passwordless_creation": true` instead of a
password. This does not change PostgreSQL authentication rules.

| Exit code | Meaning |
| --- | --- |
| 0 | Ready, or authorized changes and required verification completed |
| 1 | Runtime failure or unknown outcome; completed changes may remain |
| 2 | Invalid input, incompatible mode, or unsafe credentials file |
| 3 | Writer initialization lock is held |
| 4 | Configuration or necessary changes are required; no changes started |
| 5 | Unsupported ownership, structure or role state; no changes started |
| 130 | Interrupted; inspect the reported partial results |

Structured events are stored under `LOG_DIR/setup/`. Terminal output is for people; use the JSONL
log and exit code for automation. A missing final event is not proof of successful completion.

## Compatibility and recovery

Different software versions do not automatically imply database migration. Standard v0.3.0
databases need no structural migration for v0.4.0. Setup preserves existing data and database identity;
it can add missing registered API tables. Unknown structures are not automatically repaired.

If final authentication fails, choose **Correct credentials and verify only**, then replace the relevant credential. This checks access without repeating completed database changes.
If the target itself changed, inspect it and review a new plan instead. Existing
passwords must be changed by an administrator outside setup, for example with psql's hidden
`\password` prompt. Do not delete the database to fix an account password.

Setup no longer exports SQL/script bundles. Manual [database operations](../operations/database.md)
and `init-db` remain available. Use the reader account for [reading data](reading-data.md), and
keep writer access for downloader operations.

Interactive cancellation before changes returns 0; unresolved Unknown/Unsupported return 1/5.
Ctrl+C or EOF returns 130. Declining configuration saving after database readiness returns 0
with Not saved; an unresolved save failure returns 1.
