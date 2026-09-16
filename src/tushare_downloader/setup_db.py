"""Database setup facts and finite operations. No terminal input or credential persistence."""

import re
from dataclasses import replace

from psycopg import sql

from .apis import APIS
from .storage import StorageError, Store, connect


def name(value):
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value):
        raise ValueError("Setup names must use lowercase letters, digits and underscores (1..63).")
    return value


def build_plan(state):
    if state["kind"] not in {"missing", "empty", "managed"} or not state["roles_safe"]:
        raise ValueError(
            "Blocked: database ownership, structure, or shared role privileges conflict."
        )
    plan = []
    if not state["writer_exists"]:
        plan.append("create-writer")
    if not state["reader_exists"]:
        plan.append("create-reader")
    if state["kind"] == "missing":
        plan.append("create-database")
    if state["kind"] in {"missing", "empty"} or state["missing"]:
        plan.append("initialize")
    if state["grants_needed"] or state["kind"] != "managed" or not state["reader_exists"]:
        plan.append("grants")
    return plan


def timeouts(conn, seconds):
    conn.execute(
        "SELECT set_config('statement_timeout',%s,false)", (str(max(1, int(seconds * 1000))),)
    )
    conn.execute(
        "SELECT set_config('lock_timeout',%s,false)", (str(max(1, int(min(5, seconds) * 1000))),)
    )


def snapshot(settings, administrator, reader):
    writer = name(settings.pg_user)
    reader = name(reader)
    name(settings.pg_database)
    if writer == reader:
        raise StorageError("Writer and reader must be different roles.")
    result = {
        "kind": "missing",
        "writer_exists": False,
        "reader_exists": False,
        "roles_safe": True,
        "missing": [],
        "grants_needed": True,
        "database": settings.pg_database,
        "writer": writer,
        "reader": reader,
        "roles": {},
        "database_id": None,
    }
    with connect(administrator) as conn:
        timeouts(conn, settings.inspect_timeout.total_seconds())
        db = conn.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
            (settings.pg_database,),
        ).fetchone()
        result["owner"] = db[0] if db else None
        for label, role in (("writer", writer), ("reader", reader)):
            row = conn.execute(
                "SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,"
                "rolbypassrls FROM pg_roles WHERE rolname=%s",
                (role,),
            ).fetchone()
            result[label + "_exists"] = row is not None
            result["roles"][role] = row
            if row is not None and (not row[0] or any(row[1:])):
                result["roles_safe"] = False
            if row:
                members = conn.execute(
                    "SELECT rolname FROM pg_roles WHERE oid<>(SELECT oid "
                    "FROM pg_roles WHERE rolname=%s) AND pg_has_role(%s,oid,'MEMBER') ORDER BY rolname",
                    (role, role),
                ).fetchall()
                # The selected writer owning this database is intentionally an
                # implicit pg_database_owner member. This is not a grantable,
                # cluster-wide privilege escalation. Reader membership stays blocked.
                if label == "writer" and db and db[0] == writer:
                    members = [entry for entry in members if entry[0] != "pg_database_owner"]
                result["roles"][role + " memberships"] = members
                # A shared elevated membership must be reviewed, never silently altered.
                if members:
                    result["roles_safe"] = False
        if not db:
            return result
    with connect(replace(administrator, pg_database=settings.pg_database)) as conn:
        timeouts(conn, settings.inspect_timeout.total_seconds())
        store = Store(conn)
        if store._exists("meta", "schema_info"):
            try:
                identity, specs = store.identity()
                result["database_id"] = str(identity)
                result["specs"] = specs
                for api in APIS.values():
                    if api.name in specs:
                        store.validate(api)
                    elif store._exists("raw", api.name):
                        raise StorageError("Unregistered raw table.")
                    else:
                        result["missing"].append(api.name)
                owners = conn.execute(
                    "SELECT DISTINCT pg_get_userbyid(c.relowner) FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('raw','meta') "
                    "AND c.relkind='r'"
                ).fetchall()
                if owners != [(writer,)] or result["owner"] != writer:
                    raise StorageError("Managed objects have a different owner.")
                result["kind"] = "managed"
            except StorageError as error:
                result.update(kind="incompatible", reason=str(error))
        else:
            objects = conn.execute(
                "SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg_%%' "
                "AND nspname NOT IN ('information_schema','public') UNION ALL "
                "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' UNION ALL SELECT 1 FROM pg_proc p JOIN pg_namespace n "
                "ON n.oid=p.pronamespace WHERE n.nspname='public' LIMIT 1"
            ).fetchone()
            result["kind"] = (
                "external" if objects else ("empty" if db[0] == writer else "foreign-empty")
            )
        if result["reader_exists"]:
            unsafe = conn.execute(
                "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname NOT LIKE 'pg_%%' AND n.nspname <> 'information_schema' AND "
                "(c.relowner=(SELECT oid FROM pg_roles WHERE rolname=%s) OR "
                "has_table_privilege(%s,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')) LIMIT 1",
                (reader, reader),
            ).fetchone()
            create = conn.execute(
                "SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg_%%' "
                "AND nspname<>'information_schema' AND has_schema_privilege(%s,oid,'CREATE') LIMIT 1",
                (reader,),
            ).fetchone()
            functions = conn.execute(
                "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace "
                "WHERE p.prosecdef AND n.nspname NOT LIKE 'pg_%%' AND has_function_privilege(%s,p.oid,'EXECUTE') LIMIT 1",
                (reader,),
            ).fetchone()
            if unsafe or create or functions:
                result["roles_safe"] = False
            if result["kind"] == "managed":
                schemas = all(
                    conn.execute(
                        "SELECT has_schema_privilege(%s,%s,'USAGE')", (reader, s)
                    ).fetchone()[0]
                    for s in ("raw", "meta")
                )
                tables = all(
                    conn.execute(
                        "SELECT has_table_privilege(%s,%s,'SELECT')", (reader, t)
                    ).fetchone()[0]
                    for t in ["meta.schema_info", "meta.slices"]
                    + ["raw." + a for a in APIS if a not in result["missing"]]
                )
                defaults = conn.execute(
                    "SELECT 1 FROM pg_default_acl d JOIN pg_namespace n ON n.oid=d.defaclnamespace "
                    "CROSS JOIN LATERAL aclexplode(d.defaclacl) a WHERE d.defaclrole=(SELECT oid FROM pg_roles WHERE rolname=%s) "
                    "AND n.nspname='raw' AND d.defaclobjtype='r' AND a.grantee=(SELECT oid FROM pg_roles WHERE rolname=%s) "
                    "AND a.privilege_type='SELECT'",
                    (writer, reader),
                ).fetchone()
                database_connect = conn.execute(
                    "SELECT has_database_privilege(%s,%s,'CONNECT')",
                    (reader, settings.pg_database),
                ).fetchone()[0]
                result["grants_needed"] = not (database_connect and schemas and tables and defaults)
    return result


def statements(action, settings, reader, password=None):
    writer = name(settings.pg_user)
    reader = name(reader)
    if action in ("create-writer", "create-reader"):
        role = writer if action == "create-writer" else reader
        base = sql.SQL(
            "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
        ).format(sql.Identifier(role))
        return [
            base
            + (sql.SQL(" PASSWORD {} ").format(sql.Literal(password)) if password else sql.SQL(""))
        ]
    if action == "create-database":
        return [
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(name(settings.pg_database)), sql.Identifier(writer)
            )
        ]
    if action == "grants":
        return [
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                sql.Identifier(settings.pg_database), sql.Identifier(reader)
            ),
            sql.SQL("GRANT USAGE ON SCHEMA raw,meta TO {}").format(sql.Identifier(reader)),
            *[
                sql.SQL("GRANT SELECT ON {} TO {}").format(
                    sql.Identifier("raw", api), sql.Identifier(reader)
                )
                for api in APIS
            ],
            sql.SQL("GRANT SELECT ON meta.schema_info,meta.slices TO {}").format(
                sql.Identifier(reader)
            ),
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA raw GRANT SELECT ON TABLES TO {}"
            ).format(sql.Identifier(writer), sql.Identifier(reader)),
        ]
    raise ValueError("Unsupported setup operation.")


def apply_step(expected, action, settings, administrator, reader, password=None):
    actual = snapshot(settings, administrator, reader)
    if actual != expected or action not in build_plan(actual):
        raise StorageError("Setup state changed; inspect and confirm a new plan.")
    connection = settings if action == "initialize" else administrator
    if action in ("initialize", "grants"):
        connection = replace(connection, pg_database=settings.pg_database)
    with connect(connection) as conn:
        timeouts(conn, settings.setup_step_timeout.total_seconds())
        if action == "initialize":
            store = Store(conn)
            with store.writer():
                store.initialize()
        elif action == "create-database":
            conn.execute(statements(action, settings, reader)[0])
        else:
            with conn.transaction():
                for statement in statements(action, settings, reader, password):
                    conn.execute(statement)
    try:
        return snapshot(settings, administrator, reader)
    except Exception:
        # Mutation returned successfully; a failed follow-up inspection must not
        # be reported as an SQL rejection proving that nothing committed.
        raise RuntimeError("Change completed but follow-up inspection failed.") from None


def verify(settings, reader=None):
    with connect(settings) as conn:
        timeouts(conn, settings.inspect_timeout.total_seconds())
        if conn.info.user != settings.pg_user:
            raise StorageError("Unexpected login identity.")
        store = Store(conn)
        for api in APIS.values():
            store.validate(api)
            conn.execute(
                sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier("raw", api.name))
            ).fetchone()
        return {
            "user": conn.info.user,
            "database": conn.info.dbname,
            "database_id": str(store.identity()[0]),
        }
