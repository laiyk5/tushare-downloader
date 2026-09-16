"""Bounded read-only observations; no downloader writer lock, reports, or HTTP."""

from datetime import UTC, datetime
from time import monotonic

import psycopg
from psycopg import sql

from .apis import APIS
from .bounded import DeadlineExceeded, bounded
from .contracts import VERSIONS
from .storage import StorageError, Store, connect


def _read(settings, name, counts):
    api = APIS[name]
    result = {
        "Dataset": name,
        "Table": "raw." + name,
        "State": "Ready",
        "Expected schema": VERSIONS[(1, name, api.spec_version)],
        "Installed schema": "Unavailable",
        "Observed at": datetime.now(UTC).isoformat(),
        "ok": True,
    }
    with connect(settings) as conn:
        conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        stop = monotonic() + settings.inspect_timeout.total_seconds()

        def query(statement, params=()):
            ms = max(1, int((stop - monotonic()) * 1000))
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(ms),))
            return conn.execute(statement, params)

        store = Store(conn)
        if not store._exists("meta", "schema_info"):
            occupied = query(
                "SELECT 1 FROM pg_namespace WHERE nspname IN ('raw','meta')"
            ).fetchone()
            result.update(State="Incompatible" if occupied else "Not initialized", ok=not occupied)
            return result
        for table in ("meta.schema_info", "meta.slices"):
            allowed = query(
                "SELECT has_table_privilege(current_user,%s,'SELECT')", (table,)
            ).fetchone()[0]
            if not allowed:
                result.update(
                    State="Permission denied", ok=False, Detail="SELECT required on " + table
                )
                return result
        identity, specs = store.identity()
        result["Database ID"] = str(identity)
        others = sorted(set(specs) - set(APIS))
        if others:
            result["Other registered datasets"] = ", ".join(others)
        exists = store._exists("raw", name)
        if name not in specs and not exists:
            result.update(State="Not initialized", **{"Installed schema": "Not initialized"})
            return result
        if (
            exists
            and not query(
                "SELECT has_table_privilege(current_user,%s,'SELECT')", ("raw." + name,)
            ).fetchone()[0]
        ):
            result.update(
                State="Permission denied", ok=False, Detail="SELECT required on raw." + name
            )
            return result
        result["Installed schema"] = VERSIONS.get((1, name, specs.get(name)), "Unknown")
        try:
            store.validate(api)
        except StorageError as error:
            result.update(State="Incompatible", ok=False, Detail=str(error))
            return result

        def metric(label, function):
            query("SAVEPOINT metric")
            try:
                result[label] = function()
            except psycopg.Error as error:
                conn.execute("ROLLBACK TO SAVEPOINT metric")
                result[label] = "Timed out" if error.sqlstate == "57014" else "Unavailable"
                result.update(ok=False, State="Partial inspection")
            finally:
                query("RELEASE SAVEPOINT metric")

        metric(
            "Storage bytes (total / table / indexes)",
            lambda: query(
                "SELECT pg_total_relation_size(%s::regclass), pg_table_size(%s::regclass), "
                "pg_indexes_size(%s::regclass)",
                ("raw." + name,) * 3,
            ).fetchone(),
        )
        if api.query_kind == "snapshot":
            result["Latest data"] = "N/A (snapshot)"
        else:
            metric(
                "Latest data",
                lambda: (
                    query(
                        sql.SQL("SELECT max(trade_date) FROM {} WHERE NOT _is_stale").format(
                            sql.Identifier("raw", name)
                        )
                    ).fetchone()[0]
                    or "No active data"
                ),
            )
        metric(
            "Last successful fetch (UTC)",
            lambda: (
                query(
                    "SELECT max(last_success_at) FROM meta.slices WHERE api=%s", (name,)
                ).fetchone()[0]
                or "Never"
            ),
        )
        metric(
            "Last recorded attempt (UTC)",
            lambda: (
                query(
                    "SELECT max(last_attempt_at) FROM meta.slices WHERE api=%s", (name,)
                ).fetchone()[0]
                or "Never"
            ),
        )
        metric(
            "Latest attempt outcomes",
            lambda: query(
                "SELECT outcome, count(*) FROM meta.slices WHERE api=%s AND last_attempt_at="
                "(SELECT max(last_attempt_at) FROM meta.slices WHERE api=%s) GROUP BY outcome "
                "ORDER BY outcome",
                (name, name),
            ).fetchall(),
        )
        metric(
            "Recorded spec versions",
            lambda: query(
                "SELECT DISTINCT spec_version FROM meta.slices WHERE api=%s ORDER BY spec_version",
                (name,),
            ).fetchall(),
        )
        recorded_versions = result["Recorded spec versions"]
        if isinstance(recorded_versions, list) and any(
            version != api.spec_version for (version,) in recorded_versions
        ):
            result["Recorded history compatibility"] = (
                "Incompatible request spec versions are present; historical timestamps "
                "do not establish successful downloads under the current request spec."
            )
        if counts:
            metric(
                "Active / Stale rows",
                lambda: query(
                    sql.SQL(
                        "SELECT count(*) FILTER (WHERE NOT _is_stale), count(*) FILTER (WHERE _is_stale) "
                        "FROM {}"
                    ).format(sql.Identifier("raw", name))
                ).fetchone(),
            )
        conn.execute("ROLLBACK")
    return result


def inspect_dataset(settings, name, counts=False):
    try:
        return bounded(
            _read,
            settings,
            name,
            counts,
            seconds=settings.connect_timeout + settings.inspect_timeout.total_seconds(),
        )
    except DeadlineExceeded:
        return {"Dataset": name, "State": "Timed out", "ok": False}
    except RuntimeError as error:
        message = str(error)
        sqlstate = getattr(error, "sqlstate", None)
        if sqlstate == "57014":
            state = "Timed out"
        elif sqlstate == "42501" or "InsufficientPrivilege" in message:
            state = "Permission denied"
        else:
            state = "Unavailable"
        return {"Dataset": name, "State": state, "Detail": message, "ok": False}
