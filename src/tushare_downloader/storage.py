"""PostgreSQL ownership checks and atomic slice writes. No HTTP inside transactions."""

from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from .apis import APIS
from .planning import Observation

APPLICATION = "tushare-downloader"
SCHEMA_VERSION = 1
LOCK_KEY = 780213409


class StorageError(Exception):
    """Safe storage diagnostic."""


class BusyError(StorageError):
    """Another writer holds the database lock."""


class CommitUnknown(StorageError):
    """The server may have committed; do not replay automatically."""

    def __init__(self, message, *, interrupted=False):
        super().__init__(message)
        self.interrupted = interrupted


def connect(settings):
    return psycopg.connect(
        host=settings.pg_host,
        port=settings.pg_port,
        dbname=settings.pg_database,
        user=settings.pg_user,
        password=settings.pg_password,
        sslmode=settings.pg_sslmode,
        connect_timeout=settings.connect_timeout,
        autocommit=True,
    )


def columns(api):
    types = {"text": "text", "date": "date", "decimal": "numeric"}
    return {f.name: (types[f.kind], not f.nullable) for f in api.fields} | {
        "_is_stale": ("boolean", True),
        "_stale_at": ("timestamp with time zone", False),
        "_last_seen_at": ("timestamp with time zone", True),
        "_updated_at": ("timestamp with time zone", True),
    }


META_COLUMNS = {
    "schema_info": {
        "singleton": ("boolean", True),
        "database_id": ("uuid", True),
        "application_id": ("text", True),
        "schema_version": ("integer", True),
        "specs": ("jsonb", True),
    },
    "slices": {
        "api": ("text", True),
        "block_id": ("bigint", True),
        "spec_version": ("text", True),
        "requested_start": ("date", True),
        "requested_end": ("date", True),
        "last_attempt_at": ("timestamp with time zone", True),
        "outcome": ("text", True),
        "last_success_at": ("timestamp with time zone", False),
        "last_result_kind": ("text", False),
        "last_row_count": ("bigint", False),
        "last_reconciled_at": ("timestamp with time zone", False),
        "local_active_count": ("bigint", False),
        "local_stale_count": ("bigint", False),
    },
}


@dataclass
class Counts:
    inserted: int = 0
    changed: int = 0
    unchanged: int = 0
    reactivated: int = 0
    stale: int = 0


class Store:
    def __init__(self, conn):
        if not conn.autocommit:
            raise StorageError("数据库连接必须使用 autocommit，分段事务由存储层管理。")
        self.conn = conn

    @contextmanager
    def writer(self):
        if not self.conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]:
            raise BusyError("当前数据库已有下载器写入实例。")
        try:
            yield self
        finally:
            if not self.conn.closed:
                with suppress(psycopg.Error):
                    self.conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))

    @contextmanager
    def transaction(self):
        # Explicit COMMIT lets us distinguish statement failure from lost acknowledgement.
        self.conn.execute("BEGIN")
        try:
            yield
        except BaseException:
            if not self.conn.closed:
                with suppress(psycopg.Error):
                    self.conn.execute("ROLLBACK")
            raise
        try:
            self.conn.execute("COMMIT")
        except KeyboardInterrupt:
            raise CommitUnknown("提交时被中断，结果未知；请重新自检。", interrupted=True) from None
        except (psycopg.OperationalError, psycopg.InterfaceError):
            raise CommitUnknown("提交确认丢失，结果未知；停止本次执行，请重新自检。") from None

    def _exists(self, schema, name):
        return (
            self.conn.execute("SELECT to_regclass(%s)", (f"{schema}.{name}",)).fetchone()[0]
            is not None
        )

    def _validate_table(self, schema, name, expected, key):
        actual = self.conn.execute(
            """
            SELECT column_name, data_type, is_nullable='NO'
            FROM information_schema.columns WHERE table_schema=%s AND table_name=%s
            ORDER BY ordinal_position""",
            (schema, name),
        ).fetchall()
        if {n: (t, required) for n, t, required in actual} != expected:
            raise StorageError(f"{schema}.{name} 列或类型不兼容；未自动修改。")
        primary = self.conn.execute(
            """
            SELECT a.attname FROM pg_index i
            JOIN pg_class c ON c.oid=i.indrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
            JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=k.attnum
            WHERE n.nspname=%s AND c.relname=%s AND i.indisprimary ORDER BY k.ord
            """,
            (schema, name),
        ).fetchall()
        if tuple(row[0] for row in primary) != tuple(key):
            raise StorageError(f"{schema}.{name} 主键不兼容。")

    def identity(self):
        if not self._exists("meta", "schema_info"):
            raise StorageError("数据库尚未初始化；请运行 init-db。")
        for name, expected in META_COLUMNS.items():
            self._validate_table(
                "meta",
                name,
                expected,
                ("singleton",) if name == "schema_info" else ("api", "block_id"),
            )
        rows = self.conn.execute(
            "SELECT database_id, application_id, schema_version, specs, singleton FROM meta.schema_info"
        ).fetchall()
        if (
            len(rows) != 1
            or rows[0][1:3] != (APPLICATION, SCHEMA_VERSION)
            or rows[0][4] is not True
        ):
            raise StorageError("数据库身份或 schema 版本不兼容。")
        if not isinstance(rows[0][3], dict):
            raise StorageError("数据库接口版本信息无效。")
        return rows[0][0], rows[0][3]

    def validate(self, api):
        identity, specs = self.identity()
        if specs.get(api.name) != api.spec_version:
            raise StorageError(f"{api.name} 尚未初始化或 spec 版本不兼容。")
        self._validate_table("raw", api.name, columns(api), api.unique_key)
        return identity

    def initialize(self):
        with self.transaction():
            if not self._exists("meta", "schema_info"):
                occupied = self.conn.execute(
                    "SELECT nspname FROM pg_namespace WHERE nspname IN ('raw','meta')"
                ).fetchall()
                if occupied:
                    raise StorageError("发现未受管理的 raw/meta schema；拒绝接管。")
                self.conn.execute("CREATE SCHEMA raw")
                self.conn.execute("CREATE SCHEMA meta")
                self.conn.execute("""CREATE TABLE meta.schema_info (
                    singleton boolean PRIMARY KEY CHECK(singleton),
                    database_id uuid NOT NULL, application_id text NOT NULL,
                    schema_version integer NOT NULL, specs jsonb NOT NULL)""")
                self.conn.execute("""CREATE TABLE meta.slices (
                    api text NOT NULL, block_id bigint NOT NULL, spec_version text NOT NULL,
                    requested_start date NOT NULL, requested_end date NOT NULL,
                    last_attempt_at timestamptz NOT NULL, outcome text NOT NULL,
                    last_success_at timestamptz, last_result_kind text, last_row_count bigint,
                    last_reconciled_at timestamptz, local_active_count bigint,
                    local_stale_count bigint, PRIMARY KEY(api, block_id))""")
                self.conn.execute(
                    "INSERT INTO meta.schema_info VALUES (true,%s,%s,%s,%s)",
                    (uuid4(), APPLICATION, SCHEMA_VERSION, Jsonb({})),
                )
            identity, specs = self.identity()
            for api in APIS.values():
                if api.name in specs:
                    self.validate(api)
                    continue
                if self._exists("raw", api.name):
                    raise StorageError(f"拒绝接管已有 raw.{api.name}。")
                defs = [
                    sql.SQL("{} {} {}").format(
                        sql.Identifier(n), sql.SQL(t), sql.SQL("NOT NULL" if required else "")
                    )
                    for n, (t, required) in columns(api).items()
                ]
                defs.append(
                    sql.SQL("PRIMARY KEY ({})").format(
                        sql.SQL(",").join(map(sql.Identifier, api.unique_key))
                    )
                )
                self.conn.execute(
                    sql.SQL("CREATE TABLE {} ({})").format(
                        sql.Identifier("raw", api.name), sql.SQL(",").join(defs)
                    )
                )
                if api.query_kind == "time-range":
                    self.conn.execute(
                        sql.SQL("CREATE INDEX ON {} (trade_date)").format(
                            sql.Identifier("raw", api.name)
                        )
                    )
                specs[api.name] = api.spec_version
            self.conn.execute("UPDATE meta.schema_info SET specs=%s", (Jsonb(specs),))
        return identity

    def _scope(self, api, block, alias=""):
        if api.query_kind == "snapshot":
            return sql.SQL("true"), ()
        col = sql.Identifier(alias, "trade_date") if alias else sql.Identifier("trade_date")
        return sql.SQL("{} BETWEEN %s AND %s").format(col), (
            block.requested_start,
            block.requested_end,
        )

    def counts(self, api, block=None):
        scope, params = self._scope(api, block) if block else (sql.SQL("true"), ())
        return self.conn.execute(
            sql.SQL("""
            SELECT count(*) FILTER(WHERE NOT _is_stale), count(*) FILTER(WHERE _is_stale)
            FROM {} WHERE {}""").format(sql.Identifier("raw", api.name), scope),
            params,
        ).fetchone()

    def latest(self, api):
        return self.conn.execute(
            sql.SQL("SELECT max(trade_date) FROM {} WHERE NOT _is_stale").format(
                sql.Identifier("raw", api.name)
            )
        ).fetchone()[0]

    def observation(self, api, block):
        row = self.conn.execute(
            """
            SELECT spec_version, requested_start, requested_end, last_success_at,
                   last_reconciled_at, last_result_kind, outcome, local_active_count,
                   local_stale_count FROM meta.slices WHERE api=%s AND block_id=%s
            """,
            (api.name, block.id),
        ).fetchone()
        if row is None:
            return None
        return Observation(
            *row[:5],
            empty=row[5] == "empty",
            failed=row[6] != "success",
            local_consistent=self.counts(api, block) == row[7:9],
        )

    def failed(self, api, block, stamp):
        with self.transaction():
            self.conn.execute(
                """
                INSERT INTO meta.slices(api,block_id,spec_version,requested_start,requested_end,
                                        last_attempt_at,outcome)
                VALUES (%s,%s,%s,%s,%s,%s,'failed')
                ON CONFLICT(api,block_id) DO UPDATE SET
                    last_attempt_at=excluded.last_attempt_at,outcome='failed'
                """,
                (
                    api.name,
                    block.id,
                    api.spec_version,
                    block.requested_start,
                    block.requested_end,
                    stamp,
                ),
            )

    def merge(self, api, block, rows, stamp: datetime, *, reconcile=False):
        if reconcile and not api.stale_scope_verified:
            raise StorageError("接口尚未验证完整核对范围，不能执行 stale 对齐。")
        if api.query_kind == "time-range":
            pos = api.field_names.index("trade_date")
            if any(not block.requested_start <= row[pos] <= block.requested_end for row in rows):
                raise StorageError("响应包含请求范围以外的日期；整段拒绝写入。")
        table = sql.Identifier("raw", api.name)
        fields = sql.SQL(",").join(map(sql.Identifier, api.field_names))
        keys = sql.SQL(" AND ").join(
            sql.SQL("t.{}=s.{}").format(sql.Identifier(k), sql.Identifier(k))
            for k in api.unique_key
        )
        changed = sql.SQL(" OR ").join(
            sql.SQL("t.{} IS DISTINCT FROM s.{}").format(sql.Identifier(f), sql.Identifier(f))
            for f in api.field_names
        )
        counts = Counts()
        with self.transaction():
            self.conn.execute(
                sql.SQL("CREATE TEMP TABLE incoming (LIKE {} INCLUDING ALL) ON COMMIT DROP").format(
                    table
                )
            )
            with self.conn.cursor().copy(
                sql.SQL("COPY incoming ({},_is_stale,_last_seen_at,_updated_at) FROM STDIN").format(
                    fields
                )
            ) as copy:
                for row in rows:
                    copy.write_row((*row, False, stamp, stamp))
            totals = self.conn.execute(
                sql.SQL("""
                SELECT count(*) FILTER(WHERE t.{} IS NULL),
                       count(*) FILTER(WHERE t._is_stale),
                       count(*) FILTER(WHERE NOT t._is_stale AND ({})),
                       count(*) FILTER(WHERE NOT t._is_stale AND NOT ({}))
                FROM incoming s LEFT JOIN {} t ON {}""").format(
                    sql.Identifier(api.unique_key[0]), changed, changed, table, keys
                )
            ).fetchone()
            counts.inserted, counts.reactivated, counts.changed, counts.unchanged = totals
            # Update even unchanged rows to record observation; _updated_at stays stable.
            assignments = [
                sql.SQL("{}=s.{}").format(sql.Identifier(f), sql.Identifier(f))
                for f in api.field_names
            ]
            self.conn.execute(
                sql.SQL("""
                UPDATE {} t SET {}, _is_stale=false, _stale_at=NULL, _last_seen_at=%s,
                    _updated_at=CASE WHEN t._is_stale OR ({}) THEN %s ELSE t._updated_at END
                FROM incoming s WHERE {}""").format(
                    table, sql.SQL(",").join(assignments), changed, keys
                ),
                (stamp, stamp),
            )
            self.conn.execute(
                sql.SQL("""
                INSERT INTO {} SELECT s.* FROM incoming s
                WHERE NOT EXISTS (SELECT 1 FROM {} t WHERE {})""").format(table, table, keys)
            )
            if reconcile and rows:
                scope, params = self._scope(api, block, "t")
                counts.stale = self.conn.execute(
                    sql.SQL("""
                    UPDATE {} t SET _is_stale=true,_stale_at=%s,_updated_at=%s
                    WHERE NOT _is_stale AND {} AND NOT EXISTS
                    (SELECT 1 FROM incoming s WHERE {})""").format(table, scope, keys),
                    (stamp, stamp, *params),
                ).rowcount
            active, stale = self.counts(api, block)
            self.conn.execute(
                """
                INSERT INTO meta.slices VALUES (%s,%s,%s,%s,%s,%s,'success',%s,%s,%s,%s,%s,%s)
                ON CONFLICT(api,block_id) DO UPDATE SET
                  spec_version=excluded.spec_version,requested_start=excluded.requested_start,
                  requested_end=excluded.requested_end,last_attempt_at=excluded.last_attempt_at,
                  outcome='success',last_success_at=excluded.last_success_at,
                  last_result_kind=excluded.last_result_kind,last_row_count=excluded.last_row_count,
                  last_reconciled_at=CASE WHEN excluded.last_reconciled_at IS NOT NULL
                    THEN excluded.last_reconciled_at
                    WHEN excluded.last_result_kind='nonempty'
                      AND meta.slices.spec_version=excluded.spec_version
                      AND meta.slices.requested_start=excluded.requested_start
                      AND meta.slices.requested_end=excluded.requested_end
                    THEN meta.slices.last_reconciled_at ELSE NULL END,
                  local_active_count=excluded.local_active_count,local_stale_count=excluded.local_stale_count
                """,
                (
                    api.name,
                    block.id,
                    api.spec_version,
                    block.requested_start,
                    block.requested_end,
                    stamp,
                    stamp,
                    "nonempty" if rows else "empty",
                    len(rows),
                    stamp if reconcile and rows else None,
                    active,
                    stale,
                ),
            )
        return counts

    def clean(self, api, *, apply=False, database=None, database_id=None):
        identity = self.validate(api)
        name = self.conn.info.dbname
        counts = self.counts(api)
        slices = self.conn.execute(
            "SELECT count(*) FROM meta.slices WHERE api=%s", (api.name,)
        ).fetchone()[0]
        if apply:
            if database != name or str(database_id) != str(identity):
                raise StorageError("清理确认的数据库名称或身份不匹配。")
            with self.transaction():
                self.conn.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier("raw", api.name)))
                self.conn.execute("DELETE FROM meta.slices WHERE api=%s", (api.name,))
        return {
            "database": name,
            "database_id": str(identity),
            "active": counts[0],
            "stale": counts[1],
            "slices": slices,
            "applied": apply,
        }
