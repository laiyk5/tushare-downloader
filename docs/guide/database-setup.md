# Set up database access

PostgreSQL must already be running. The optional setup command helps configure a connection,
initialize downloader objects, or check an existing database for an upgrade.

```bash
tushare-downloader setup
# Choose a different configuration file, including a new file:
tushare-downloader -c ./local.env setup
```

Use an interactive terminal. Choose **connection**, **initialize**, or **upgrade check**.
Supply the host, port, database, writer account and SSL settings for your server. Password input is hidden.
Setup does not install PostgreSQL, change network authentication, or upgrade the server/software.

## Review before applying

For initialization or permission changes, you can supply a temporary administrator connection.
The administrator creates missing roles/databases; the writer creates downloader tables; the reader
is used to verify access. Administrator and reader passwords are not saved.

Review the displayed database state, identity, role names and operations. Existing roles belong to
the whole PostgreSQL instance: reusing one affects everyone using that role. Setup does not reset
existing passwords or change role attributes. Conflicting ownership, extra privileges or unknown
structures require administrator attention.

To apply database changes, type the displayed target database name. Any different response cancels.
Configuration saving has a separate confirmation with hidden passwords. Saving a writer password
is optional; file permissions are restricted. Existing unrelated settings and comments are retained.
If an environment variable overrides the saved file, setup reports that the saved connection is not
the effective one. It never edits the parent shell's environment.

## Ask an administrator to run the steps

Choose script export when you cannot apply changes yourself. Select a new output directory and
read its README. The bundle separates administrator SQL, writer initialization and reader checks.
SQL files are for `psql`; the initialization file is Bash. No passwords are embedded.

Exporting does not execute changes. An **Unverified** template only helps inspect the environment;
return to setup after obtaining read access to generate a plan that can apply changes.
Do not run every file as administrator or blindly rerun a partly applied bundle.

## Existing databases and interruptions

A standard v0.3.0 database does not need a structural migration. Setup checks it and can propose
missing table initialization or reader grants. Unknown schemas are rejected; there is no automatic
schema-diff repair or general migration command.

Database creation and subsequent setup steps are not one transaction. If interrupted, previously
completed steps remain. If confirmation was lost, the result can be unknown: rerun setup to inspect
actual state before applying a new plan. Setup does not delete a database to undo partial progress.
Configuration-save failure also does not undo successful database initialization.

Manual [database setup](../operations/database.md) and `init-db` remain available.
After setup, use the reader account for [reading data](reading-data.md), and retain writer access
only for downloading and maintenance. Back up valuable data before unrelated destructive maintenance.
