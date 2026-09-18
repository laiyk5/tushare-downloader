"""One explicit, atomic suspend_d migration. No inferred schema repair."""

from psycopg import sql

from .apis.suspend_d import SUSPEND_D, SUSPEND_D_V1
from .storage import StorageError, Store, columns


def legacy_suspension(store):
    """Validate the historical shape before suggesting any migration."""
    identity, specs = store.identity()
    if specs.get("suspend_d") != "1":
        return False
    store._validate_table("raw", "suspend_d", columns(SUSPEND_D_V1), SUSPEND_D_V1.unique_key)
    return True


def preflight(store):
    identity, specs = store.identity()
    version = specs.get("suspend_d")
    if version == "2":
        store.validate(SUSPEND_D)
        return {"database_id": str(identity), "spec": "2", "state": "Already migrated"}
    if not legacy_suspension(store):
        raise StorageError("No supported migration for this suspend_d version.")
    conn = store.conn
    owners = conn.execute(
        "SELECT pg_get_userbyid(relowner)=current_user FROM pg_class WHERE oid IN ('raw.suspend_d'::regclass,'meta.schema_info'::regclass)"
    ).fetchall()
    if len(owners) != 2 or not all(row[0] for row in owners):
        raise StorageError("Migration requires ownership of raw.suspend_d and meta.schema_info.")
    types = conn.execute("SELECT DISTINCT suspend_type FROM raw.suspend_d").fetchall()
    if any(value is None or not value.strip() for (value,) in types):
        raise StorageError(
            "Migration blocked: suspend_type contains NULL or blank values. No rows changed."
        )
    primary = conn.execute(
        "SELECT oid,conname,conindid FROM pg_constraint WHERE conrelid='raw.suspend_d'::regclass AND contype='p'"
    ).fetchone()
    if not primary:
        raise StorageError("Missing historical suspend_d primary key.")
    if conn.execute(
        "SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid='raw.suspend_d'::regclass LIMIT 1"
    ).fetchone():
        raise StorageError(
            "Migration blocked by a foreign key referencing suspend_d. Review dependencies; no CASCADE."
        )
    # Ordinary views survive; dependencies on the old PK (e.g. functional grouping) cannot.
    if conn.execute(
        "SELECT 1 FROM pg_depend WHERE refclassid='pg_constraint'::regclass AND refobjid=%s AND deptype='n' LIMIT 1",
        (primary[0],),
    ).fetchone():
        raise StorageError("Migration blocked by a dependency on the old primary key.")
    return {
        "database_id": str(identity),
        "spec": "1",
        "state": "Migration needed",
        "constraint": primary[1],
    }


def preview(conn):
    store = Store(conn)
    with store.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL lock_timeout='5s'")
        conn.execute("SET LOCAL statement_timeout='60s'")
        return preflight(store)


def apply(conn, expected_identity):
    """Internal single-step convenience used by storage tests; no separate CLI."""
    from .migration_chain import REGISTRY, execute_steps, plan

    store = Store(conn)
    _, specs = store.identity()
    steps = plan(specs, {"suspend_d": "2"}, REGISTRY)
    execute_steps(
        conn,
        steps,
        expected_identity,
        specs,
        {"suspend_d-spec-1-to-2": change_suspension},
        lambda *args: None,
    )
    return {"spec": "2", "state": "Migrated" if steps else "Already migrated"}


def change_suspension(store, step):
    """One registered step; caller owns the chain lock and transaction/version update."""
    conn = store.conn
    conn.execute("LOCK TABLE raw.suspend_d IN ACCESS EXCLUSIVE MODE")
    checked = preflight(store)
    if checked["spec"] != step.source:
        raise StorageError("Unexpected suspension version during migration.")
    conn.execute(
        sql.SQL("ALTER TABLE raw.suspend_d DROP CONSTRAINT {}").format(
            sql.Identifier(checked["constraint"])
        )
    )
    conn.execute("ALTER TABLE raw.suspend_d ALTER COLUMN suspend_type SET NOT NULL")
    conn.execute(
        sql.SQL(
            "ALTER TABLE raw.suspend_d ADD CONSTRAINT {} PRIMARY KEY (ts_code, trade_date, suspend_type)"
        ).format(sql.Identifier(checked["constraint"]))
    )
    store._validate_table("raw", "suspend_d", columns(SUSPEND_D), SUSPEND_D.unique_key)
