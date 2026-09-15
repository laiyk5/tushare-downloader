"""Human-executed setup bundle; no passwords or independently maintained table DDL."""

import os
import shlex
import tempfile
from pathlib import Path

from psycopg import sql

from .setup_db import build_plan, name, statements


def guard(predicate, message):
    return (
        sql.SQL("DO $setup$ BEGIN IF NOT ({}) THEN RAISE EXCEPTION {}; END IF; END $setup$;\n")
        .format(predicate, sql.Literal(message))
        .as_string()
    )


def role_check(role, exists):
    if not exists:
        predicate = sql.SQL("NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname={})").format(
            sql.Literal(role)
        )
    else:
        predicate = sql.SQL(
            "EXISTS(SELECT 1 FROM pg_roles WHERE rolname={} AND rolcanlogin "
            "AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) "
            "AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname<>{} AND rolname<>'pg_database_owner' AND pg_has_role({},oid,'MEMBER'))"
        ).format(sql.Literal(role), sql.Literal(role), sql.Literal(role))
    return guard(predicate, "Role state changed; inspect and regenerate the bundle.")


def export_bundle(path, state, settings, administrator, reader, config_path):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError("Export destination must be a new directory.")
    writer = name(settings.pg_user)
    reader = name(reader)
    database = name(settings.pg_database)
    temporary = Path(tempfile.mkdtemp(prefix=".setup-export-", dir=path.parent))
    os.chmod(temporary, 0o700)
    files = {}
    try:
        if state is None:
            files["README.md"] = (
                "# Unverified setup template\n\nNo mutations are included. "
                "Ask the administrator to check the target database, roles, ownership and effective "
                "permissions. Then rerun setup with read access to generate a verified plan.\n"
            )
            files["04-reader-check.sql"] = (
                "\\set ON_ERROR_STOP on\nSELECT current_user,current_database();\n"
            )
        else:
            plan = build_plan(state)
            header = (
                "\\set ON_ERROR_STOP on\nSET statement_timeout='60s';\nSET lock_timeout='5s';\n"
            )
            admin = header + guard(
                sql.SQL("current_user={}").format(sql.Literal(administrator.pg_user)),
                "Use the planned administrator account.",
            )
            admin += role_check(writer, state["writer_exists"]) + role_check(
                reader, state["reader_exists"]
            )
            exists = state["kind"] != "missing"
            pred = (
                sql.SQL(
                    "EXISTS(SELECT 1 FROM pg_database WHERE datname={} AND pg_get_userbyid(datdba)={})"
                ).format(sql.Literal(database), sql.Literal(writer))
                if exists
                else sql.SQL("NOT EXISTS(SELECT 1 FROM pg_database WHERE datname={})").format(
                    sql.Literal(database)
                )
            )
            admin += guard(pred, "Database state changed; regenerate the bundle.")
            for action in plan:
                if action.startswith("create-"):
                    admin += (
                        "\n".join(s.as_string() + ";" for s in statements(action, settings, reader))
                        + "\n"
                    )
                    if action in ("create-writer", "create-reader"):
                        admin += (
                            "\\password " + (writer if action == "create-writer" else reader) + "\n"
                        )
            files["01-admin.sql"] = admin
            if "initialize" in plan:
                cfg = shlex.quote(str(Path(config_path).absolute()))
                pinned = " ".join(
                    shlex.quote(k + "=" + str(v))
                    for k, v in {
                        "PGHOST": settings.pg_host,
                        "PGPORT": settings.pg_port,
                        "PGDATABASE": database,
                        "PGUSER": writer,
                        "PGSSLMODE": settings.pg_sslmode,
                    }.items()
                )
                files["02-initialize.sh"] = (
                    "#!/usr/bin/env bash\nset -euo pipefail\n"
                    "# Target is pinned; password still comes from the selected config/environment.\n"
                    f"test -f {cfg}\n"
                    f"env {pinned} tushare-downloader -c {cfg} init-db\n"
                )
            grants = header + guard(
                sql.SQL("current_database()={} AND current_user={}").format(
                    sql.Literal(database), sql.Literal(administrator.pg_user)
                ),
                "Wrong target database.",
            )
            grants += role_check(writer, True) + role_check(reader, True)
            pred = sql.SQL(
                "EXISTS(SELECT 1 FROM meta.schema_info WHERE singleton AND application_id='tushare-downloader' "
                "AND schema_version=1)"
            )
            if state.get("database_id"):
                pred += sql.SQL(
                    " AND EXISTS(SELECT 1 FROM meta.schema_info WHERE database_id={}::uuid)"
                ).format(sql.Literal(state["database_id"]))
            grants += guard(pred, "Unexpected database identity.")
            grants += guard(
                sql.SQL(
                    "NOT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname IN ('raw','meta') AND c.relkind='r' AND pg_get_userbyid(c.relowner)<>{})"
                ).format(sql.Literal(writer)),
                "Unexpected table owner.",
            )
            if "grants" in plan:
                grants += (
                    "\n".join(s.as_string() + ";" for s in statements("grants", settings, reader))
                    + "\n"
                )
            files["03-grants.sql"] = grants
            files["04-reader-check.sql"] = (
                header
                + guard(
                    sql.SQL("current_user={} AND current_database()={}").format(
                        sql.Literal(reader), sql.Literal(database)
                    ),
                    "Use the reader in the target database.",
                )
                + "SELECT database_id FROM meta.schema_info;\nSELECT api FROM meta.slices LIMIT 1;\n"
            )
            from .apis import APIS

            for api in sorted(APIS):
                files["04-reader-check.sql"] += f'SELECT 1 FROM raw."{api}" LIMIT 1;\n'

            def psql(user, db, file):
                return " ".join(
                    shlex.quote(s)
                    for s in [
                        "psql",
                        "-h",
                        settings.pg_host,
                        "-p",
                        str(settings.pg_port),
                        "-U",
                        user,
                        "-d",
                        db,
                        "-W",
                        "-f",
                        file,
                    ]
                )

            files["README.md"] = (
                "# Database setup plan\n\nVerified at export; rechecks are required at execution. "
                "No database changes have been applied by exporting. No passwords are stored.\n\n"
                f"Target: {database}; writer: {writer}; reader: {reader}.\n\n"
                "Review TLS settings in your client; set PGSSLMODE to the agreed value. "
                "Run from this directory in the order below. SQL files require psql, not Bash. "
                "Do not wrap CREATE DATABASE in a transaction or use --single-transaction.\n\n"
                f"```bash\n{psql(administrator.pg_user, administrator.pg_database, '01-admin.sql')}\n```\n\n"
                "If 02-initialize.sh exists, first prepare the referenced downloader configuration "
                "with the writer connection and check environment overrides, then run `bash 02-initialize.sh`. "
                "It invokes the existing init-db implementation.\n\n"
                f"```bash\n{psql(administrator.pg_user, database, '03-grants.sql')}\n"
                f"{psql(reader, database, '04-reader-check.sql')}\n```\n\n"
                "Enter passwords interactively. If a step fails, retain completed objects and rerun "
                "setup to inspect actual state and produce a new plan. Do not rerun a partly applied "
                "bundle blindly. Reader SELECT checks do not prove arbitrary custom grants are safe.\n"
            )
        for filename, content in files.items():
            target = temporary / filename
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as output:
                output.write(content)
        if path.exists():
            raise ValueError("Export destination appeared during generation.")
        temporary.rename(path)
        return path
    except BaseException:
        for file in temporary.iterdir():
            file.unlink()
        temporary.rmdir()
        raise
