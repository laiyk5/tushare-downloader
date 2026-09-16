# Database setup

PostgreSQL must already be running. Use the interactive setup screen to inspect a connection,
create the required database and accounts, or complete missing tables and read permissions.

```bash
uv run tushare-downloader setup
uv run tushare-downloader -c ./research.env setup
```

## Interactive setup

Use a terminal such as Windows Terminal running WSL. Click a field directly, or use Tab and
Shift+Tab to move between controls. Enter activates a focused button; F1 opens keyboard help.
The minimum usable size is 40 columns by 20 rows. Interactive setup does not support `--plain`;
disable the `PLAIN` preference or use headless mode.

1. **Connection:** inspect the selected host, database and writer account. Existing connection
   settings are loaded from the selected file and environment. A new connection uses a separate
   `.env.new` destination and preserves the original file and database.
2. **Access:** provide the credentials needed for inspection or changes. Administrator credentials
   are temporary. Existing account passwords are used for authentication, never reset. For a new
   account, confirm the password; passwordless creation requires an explicit choice and a server
   already configured for another authentication method.
3. **Review:** check the target and necessary operations. Applying database changes requires
   typing the target database name. Editing a connection invalidates its previous check.
4. **Result:** review completed, failed, unknown and unattempted operations. Configuration saving
   is a separate confirmation, including whether to store or clear the writer password.

The log path is available while setup runs. Completed database changes remain if a later step
fails. Cancellation stops further steps, but an interrupted database operation may have an unknown
outcome. Recheck the database before trying again; setup does not blindly replay an old plan.

Saving a configuration does not change your shell environment. Environment variables take
precedence over saved values. Administrator and reader passwords are never saved to `.env`.
Use `-c` when selecting a separately saved connection file.

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

If final authentication fails, choose **Edit verification credentials**, correct the password, and
use **Retry access verification**. This checks access without repeating completed database changes.
If the target itself changed, inspect it and review a new plan instead. Existing
passwords must be changed by an administrator outside setup, for example with psql's hidden
`\password` prompt. Do not delete the database to fix an account password.

Setup no longer exports SQL/script bundles. Manual [database operations](../operations/database.md)
and `init-db` remain available. Use the reader account for [reading data](reading-data.md), and
keep writer access for downloader operations.
