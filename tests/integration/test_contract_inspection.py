import pytest
from psycopg.conninfo import conninfo_to_dict

from tushare_downloader.apis import get_api
from tushare_downloader.storage import StorageError


def test_numeric_typmod_is_not_same_contract(db):
    db.initialize()
    db.conn.execute("ALTER TABLE raw.daily ALTER COLUMN close TYPE numeric(10,2)")
    with pytest.raises(StorageError):
        db.validate(get_api("daily"))


def test_view_cannot_impersonate_managed_table(db):
    db.initialize()
    db.conn.execute("ALTER TABLE raw.daily RENAME TO displaced_daily")
    db.conn.execute("CREATE VIEW raw.daily AS SELECT * FROM raw.displaced_daily")
    with pytest.raises(StorageError):
        db.validate(get_api("daily"))


def test_inspect_empty_snapshot_and_daily(db):
    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import _read

    db.initialize()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    daily = _read(cfg, "daily", True)
    assert daily["ok"]
    assert daily["Latest data"] == "No active data"
    assert daily["Active / Stale rows"] == (0, 0)
    assert daily["Last successful fetch (UTC)"] == "Never"
    assert daily["Installed schema"] == "1.0.0"
    assert _read(cfg, "stock_basic", False)["Latest data"] == "N/A (snapshot)"


def test_read_does_not_take_writer_lock(db):
    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import inspect_dataset

    db.initialize()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    with db.writer():
        assert inspect_dataset(cfg, "daily")["ok"]


@pytest.mark.parametrize("empty", [False, True])
def test_inspect_preserves_success_when_later_attempts_fail(db, empty):
    from datetime import UTC, date, datetime, timedelta

    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import _read
    from tushare_downloader.planning import Block

    db.initialize()
    api = get_api("daily")
    day = date(2026, 8, 3)
    stamp = datetime(2026, 8, 4, tzinfo=UTC)
    first = Block(1, day, day, day, day)
    second = Block(
        2,
        day + timedelta(days=1),
        day + timedelta(days=1),
        day + timedelta(days=1),
        day + timedelta(days=1),
    )
    rows = [] if empty else [("000001.SZ", day, *[None for _ in api.fields[2:]])]
    db.merge(api, first, rows, stamp)
    later = stamp + timedelta(hours=1)
    db.failed(api, first, later)
    db.merge(api, second, [], later)
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    before = db.conn.execute("SELECT * FROM meta.slices ORDER BY block_id").fetchall()
    result = _read(cfg, "daily", True)
    assert result["ok"]
    assert result["Last successful fetch (UTC)"] == later
    assert result["Last recorded attempt (UTC)"] == later
    assert result["Latest attempt outcomes"] == [("failed", 1), ("success", 1)]
    assert result["Latest data"] == ("No active data" if empty else day)
    assert result["Active / Stale rows"] == (0 if empty else 1, 0)
    assert db.conn.execute("SELECT * FROM meta.slices ORDER BY block_id").fetchall() == before

    newest = later + timedelta(hours=1)
    db.failed(api, second, newest)
    result = _read(cfg, "daily", False)
    assert result["Last successful fetch (UTC)"] == later
    assert result["Last recorded attempt (UTC)"] == newest
    assert result["Latest attempt outcomes"] == [("failed", 1)]
    assert "Active / Stale rows" not in result


def test_inspect_marks_old_observations_without_relabeling_installed_schema(db):
    from datetime import UTC, date, datetime

    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import _read
    from tushare_downloader.planning import Block

    db.initialize()
    day = date(2026, 8, 3)
    stamp = datetime(2026, 8, 4, tzinfo=UTC)
    db.merge(get_api("daily"), Block(1, day, day, day, day), [], stamp)
    db.conn.execute("UPDATE meta.slices SET spec_version='old'")
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    result = _read(cfg, "daily", False)
    assert result["Installed schema"] == "1.0.0"
    assert result["Last successful fetch (UTC)"] == stamp
    assert "incompatible" in result["Recorded history compatibility"].lower()
    assert db.conn.execute("SELECT spec_version FROM meta.slices").fetchone() == ("old",)


@pytest.mark.parametrize("failed_metric", ["storage", "success_time"])
@pytest.mark.parametrize("sqlstate,expected", [("42501", "Unavailable"), ("57014", "Timed out")])
def test_inspect_metric_error_rolls_back_savepoint_and_retains_other_fields(
    db, monkeypatch, failed_metric, sqlstate, expected
):
    from contextlib import contextmanager

    from tushare_downloader import inspection
    from tushare_downloader.config import Settings

    db.initialize()
    original_connect = inspection.connect
    statements = []
    injected = []

    class Connection:
        def __init__(self, conn):
            self.conn = conn

        def __getattr__(self, name):
            return getattr(self.conn, name)

        def execute(self, statement, params=()):
            text = statement if isinstance(statement, str) else statement.as_string(self.conn)
            statements.append(text)
            marker = (
                "pg_total_relation_size" if failed_metric == "storage" else "max(last_success_at)"
            )
            if marker in text and not injected:
                injected.append(True)
                # A real server error aborts the transaction until ROLLBACK TO SAVEPOINT.
                return self.conn.execute(
                    "DO $$ BEGIN RAISE EXCEPTION 'fixture-only failure' USING ERRCODE = '"
                    + sqlstate
                    + "'; END $$"
                )
            return self.conn.execute(statement, params)

    @contextmanager
    def connect(settings):
        with original_connect(settings) as conn:
            yield Connection(conn)

    monkeypatch.setattr(inspection, "connect", connect)
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    result = inspection._read(cfg, "daily", True)
    assert injected == [True]
    assert result["State"] == "Partial inspection" and not result["ok"]
    key = (
        "Storage bytes (total / table / indexes)"
        if failed_metric == "storage"
        else "Last successful fetch (UTC)"
    )
    assert result[key] == expected
    assert result["Installed schema"] == "1.0.0"
    assert result["Latest data"] == "No active data"
    assert result["Last recorded attempt (UTC)"] == "Never"
    assert result["Active / Stale rows"] == (0, 0)
    assert "ROLLBACK TO SAVEPOINT metric" in statements
    if failed_metric == "success_time":
        assert isinstance(result["Storage bytes (total / table / indexes)"], tuple)
    else:
        assert result["Last successful fetch (UTC)"] == "Never"
    assert db.conn.execute("SELECT count(*) FROM meta.slices").fetchone()[0] == 0


@pytest.mark.parametrize("table", ["meta.schema_info", "raw.daily"])
def test_inspect_real_ddl_lock_wait_is_bounded_and_recoverable(db, table):
    import multiprocessing
    from datetime import timedelta
    from time import monotonic

    import psycopg
    from psycopg import sql

    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import inspect_dataset

    db.initialize()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
        connect_timeout=1,
        inspect_timeout=timedelta(seconds=1),
    )
    children = {child.pid for child in multiprocessing.active_children()}
    with psycopg.connect(db.test_dsn) as holder:
        holder.execute(
            sql.SQL("LOCK TABLE {} IN ACCESS EXCLUSIVE MODE").format(
                sql.Identifier(*table.split("."))
            )
        )
        started = monotonic()
        result = inspect_dataset(cfg, "daily")
        elapsed = monotonic() - started
        assert not result["ok"]
        assert result["State"] in {"Timed out", "Partial inspection"}, result
        if result["State"] == "Partial inspection":
            assert "Timed out" in result.values()
        assert elapsed < 4, elapsed  # two-second total budget plus termination allowance
        assert {child.pid for child in multiprocessing.active_children()} <= children
    assert inspect_dataset(cfg, "daily")["ok"]


@pytest.mark.parametrize(
    "ddl,compatible",
    [
        ("ALTER TABLE raw.daily DROP COLUMN close", False),
        ("ALTER TABLE raw.daily ADD COLUMN unexpected text", False),
        ("ALTER TABLE raw.daily ALTER COLUMN close SET NOT NULL", False),
        ("ALTER TABLE raw.daily ALTER COLUMN _is_stale DROP NOT NULL", False),
        (
            "ALTER TABLE raw.daily DROP CONSTRAINT daily_pkey; ALTER TABLE raw.daily ADD PRIMARY KEY(trade_date,ts_code)",
            False,
        ),
        ("CREATE INDEX extra_daily_close ON raw.daily(close)", True),
        ("ALTER TABLE raw.daily ALTER COLUMN close TYPE decimal", True),
    ],
)
def test_physical_schema_drift_is_checked_without_automatic_repair(db, ddl, compatible):
    from tushare_downloader.config import Settings
    from tushare_downloader.inspection import _read

    identity = db.initialize()
    db.conn.execute(
        "INSERT INTO raw.daily(ts_code,trade_date,close,_is_stale,_last_seen_at,_updated_at) VALUES ('fixture','2024-01-02',1,false,now(),now())"
    )
    db.conn.execute(ddl)
    before_rows = db.conn.execute("SELECT to_jsonb(t)::text FROM raw.daily t").fetchall()
    before_metadata = db.conn.execute("SELECT * FROM meta.schema_info").fetchall()
    before_columns = db.conn.execute(
        "SELECT attname,atttypid,atttypmod,attnotnull FROM pg_attribute WHERE attrelid='raw.daily'::regclass AND attnum>0 ORDER BY attnum"
    ).fetchall()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    observed = _read(cfg, "daily", False)
    assert observed["Installed schema"] == observed["Expected schema"] == "1.0.0"
    assert observed["ok"] == compatible
    if compatible:
        assert db.validate(get_api("daily")) == identity
        assert db.initialize() == identity
    else:
        assert observed["State"] == "Incompatible" and "raw.daily" in observed["Detail"]
        for operation in (lambda: db.validate(get_api("daily")), db.initialize):
            with pytest.raises(StorageError):
                operation()
    assert db.conn.execute("SELECT to_jsonb(t)::text FROM raw.daily t").fetchall() == before_rows
    assert db.conn.execute("SELECT * FROM meta.schema_info").fetchall() == before_metadata
    assert (
        db.conn.execute(
            "SELECT attname,atttypid,atttypmod,attnotnull FROM pg_attribute WHERE attrelid='raw.daily'::regclass AND attnum>0 ORDER BY attnum"
        ).fetchall()
        == before_columns
    )


@pytest.mark.parametrize(
    "case", ["unknown-spec", "unregistered", "shared-contract", "unknown-internal"]
)
def test_inspect_version_metadata_preserves_observed_identity(db, monkeypatch, case):
    from tushare_downloader.config import Settings
    from tushare_downloader.contracts import VERSIONS
    from tushare_downloader.inspection import _read

    identity = db.initialize()
    db.conn.execute(
        "INSERT INTO raw.daily(ts_code,trade_date,_is_stale,_last_seen_at,_updated_at) "
        "VALUES ('fixture','2024-01-02',false,now(),now())"
    )
    if case == "unregistered":
        db.conn.execute("UPDATE meta.schema_info SET specs=specs-'daily'")
    elif case == "unknown-internal":
        db.conn.execute("UPDATE meta.schema_info SET schema_version=999")
    else:
        db.conn.execute(
            "UPDATE meta.schema_info SET specs=jsonb_set(specs, %s, %s)",
            (["daily"], '"fixture-spec"'),
        )
        if case == "shared-contract":
            monkeypatch.setitem(VERSIONS, (1, "daily", "fixture-spec"), "1.0.0")

    def contents():
        return tuple(
            db.conn.execute(q).fetchall()
            for q in (
                "SELECT * FROM meta.schema_info",
                "SELECT * FROM meta.slices",
                "SELECT * FROM raw.daily",
            )
        )

    before = contents()
    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    result = _read(cfg, "daily", False)
    assert result["Database ID"] == str(identity)
    assert result["Expected schema"] == "1.0.0"
    assert result["Installed schema"] == ("1.0.0" if case == "shared-contract" else "Unknown")
    assert not result["ok"] and result["State"] == "Incompatible"
    # Mapping two request specs to one table contract does not authorize unsupported requests.
    for action in (lambda: db.validate(get_api("daily")), db.initialize):
        with pytest.raises(StorageError):
            action()
        assert contents() == before


def test_reader_filter_keeps_delisted_nonstale_stock(db):
    from datetime import UTC, date, datetime

    from tushare_downloader.planning import Block

    db.initialize()
    api = get_api("stock_basic")

    def row(code, status):
        values = [None] * len(api.fields)
        values[0] = code
        values[api.field_names.index("list_status")] = status
        return tuple(values)

    day = date(2024, 1, 2)
    db.merge(
        api,
        Block(0, day, day, day, day),
        [row("active", "L"), row("delisted", "D"), row("stale", "D")],
        datetime(2024, 1, 3, tzinfo=UTC),
    )
    db.conn.execute("UPDATE raw.stock_basic SET _is_stale=true WHERE ts_code='stale'")
    assert db.conn.execute(
        "SELECT ts_code,list_status FROM raw.stock_basic WHERE NOT _is_stale ORDER BY ts_code"
    ).fetchall() == [("active", "L"), ("delisted", "D")]


def test_inspect_read_only_scope_and_optional_exact_counts(db, monkeypatch):
    from contextlib import contextmanager

    import psycopg

    import tushare_downloader.inspection as inspection
    from tushare_downloader.config import Settings

    cfg = Settings(
        pg_host=db.conn.info.host,
        pg_port=db.conn.info.port,
        pg_database="tushare_test",
        pg_user="tushare_test",
        pg_password=conninfo_to_dict(db.test_dsn).get("password", ""),
    )
    assert inspection._read(cfg, "daily", False)["State"] == "Not initialized"
    db.initialize()
    db.conn.execute(
        "INSERT INTO raw.daily(ts_code,trade_date,_is_stale,_last_seen_at,_updated_at) VALUES ('stale','2024-01-02',true,now(),now())"
    )
    with pytest.raises(psycopg.errors.NotNullViolation):
        db.conn.execute(
            "INSERT INTO raw.daily(ts_code,trade_date,_is_stale,_last_seen_at,_updated_at) VALUES ('bad',NULL,false,now(),now())"
        )
    statements = []
    original = inspection.connect

    class Observed:
        def __init__(self, conn):
            self.conn = conn

        def __getattr__(self, name):
            return getattr(self.conn, name)

        def execute(self, statement, params=()):
            statements.append(
                statement if isinstance(statement, str) else statement.as_string(self.conn)
            )
            return self.conn.execute(statement, params)

    @contextmanager
    def connect(settings):
        with original(settings) as conn:
            yield Observed(conn)

    monkeypatch.setattr(inspection, "connect", connect)
    observed = inspection._read(cfg, "daily", False)
    assert observed["Latest data"] == "No active data"
    assert "Active / Stale rows" not in observed
    assert not any("count(" in q.lower() and '"raw"."daily"' in q for q in statements)
    assert all(
        q.split()[0].upper() in {"BEGIN", "SELECT", "SAVEPOINT", "RELEASE", "ROLLBACK"}
        for q in statements
    )
    assert (
        observed["Storage bytes (total / table / indexes)"]
        == db.conn.execute(
            "SELECT pg_total_relation_size('raw.daily'), pg_table_size('raw.daily'), pg_indexes_size('raw.daily')"
        ).fetchone()
    )
    counted = inspection._read(cfg, "daily", True)
    assert (
        counted["Active / Stale rows"]
        == db.conn.execute(
            "SELECT count(*) FILTER (WHERE NOT _is_stale),count(*) FILTER (WHERE _is_stale) FROM raw.daily"
        ).fetchone()
        == (0, 1)
    )
