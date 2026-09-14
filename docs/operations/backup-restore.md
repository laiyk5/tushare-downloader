# Backup and restore

These are manual operations, not downloader subcommands. Use PostgreSQL client tools compatible with the server. Examples use Bash and interactive passwords. On Windows, use the corresponding tools from the installation directory.

## Back up the whole database

```bash
BACKUP_DIR="$HOME/tushare-backups"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
umask 077
pg_dump -h localhost -p 5432 -U tushare_writer -W \
  -d tushare --format=custom --file="$BACKUP_DIR/tushare-$(date +%Y%m%d-%H%M%S).dump"
```

Back up raw and meta together in one consistent snapshot. Backups contain business data: store them in a restricted location outside the repository and documentation site. A single-database dump does not include role definitions; recreate required roles and permissions separately.

## Rehearse a restore

Restore into a new dedicated database, never over production. An administrator runs this SQL:

```sql
CREATE DATABASE tushare_restore_check OWNER tushare_writer;
```

Then run in Bash, substituting the actual backup path:

```bash
BACKUP_FILE="$HOME/tushare-backups/REPLACE_WITH_BACKUP.dump"
pg_restore -h localhost -p 5432 -U tushare_writer -W \
  --dbname=tushare_restore_check --no-owner --no-privileges \
  --exit-on-error --single-transaction "$BACKUP_FILE"
```

The restoring role owns objects in this example; old owner/ACL statements are skipped. Reapply [reader permissions](database.md) in the restored database. Extensions or downstream objects may need additional administrator preparation.

Verify column types, primary keys, active/stale counts, `meta.schema_info`, `meta.slices` and sample queries. Verify the reader can SELECT but cannot write. The backup's database_id is retained; cleanup still requires matching the actual database name. Decide whether to retain the rehearsal database after verification.

This procedure does not claim a particular backup has been verified. Do not substitute copying a running PostgreSQL data directory for a proper backup.
