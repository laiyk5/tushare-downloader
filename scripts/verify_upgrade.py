"""Exercise real old-package seeding and candidate validation in tushare_test only."""

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg
from psycopg import sql

from tushare_downloader.apis import APIS
from tushare_downloader.planning import Block
from tushare_downloader.storage import Store


def snapshot(conn):
    result = {}
    for schema, table in conn.execute(
        "SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('raw','meta') ORDER BY 1,2"
    ):
        rows = conn.execute(
            sql.SQL("SELECT to_jsonb(t)::text FROM {} t ORDER BY to_jsonb(t)::text").format(
                sql.Identifier(schema, table)
            )
        ).fetchall()
        result[f"{schema}.{table}"] = [row[0] for row in rows]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["seed", "check"])
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    dsn = os.environ["TEST_DATABASE_URL"]
    with psycopg.connect(dsn, autocommit=True) as conn:
        if conn.info.dbname != "tushare_test" or conn.info.user != "tushare_test":
            raise ValueError("Both database and user must be tushare_test")
        store = Store(conn)
        if args.mode == "seed":
            conn.execute("DROP SCHEMA IF EXISTS raw CASCADE")
            conn.execute("DROP SCHEMA IF EXISTS meta CASCADE")
            store.initialize()
            day = date(2026, 8, 3)
            stamp = datetime(2026, 8, 4, tzinfo=UTC)
            block = Block(1, day, day, day, day)
            for api in APIS.values():

                def row(key):
                    return tuple(
                        key
                        if f.name == "ts_code"
                        else day
                        if f.kind == "date"
                        else Decimal("1.25")
                        if f.kind == "decimal"
                        else None
                        if f.nullable
                        else "S"
                        for f in api.fields
                    )

                store.merge(api, block, [row("000001.SZ"), row("000002.SZ")], stamp)
                store.merge(api, block, [row("000001.SZ")], stamp, reconcile=True)
            args.snapshot.write_text(json.dumps(snapshot(conn), sort_keys=True), encoding="utf-8")
            print(
                "Seeded six tables with active/stale rows and observations using",
                __import__("tushare_downloader").__file__,
            )
        else:
            before = json.loads(args.snapshot.read_text())
            assert snapshot(conn) == before, "Candidate changed the database before initialization"
            for api in APIS.values():
                store.validate(api)
                assert store.counts(api) == (1, 1)
            identity = store.identity()
            for _ in range(2):
                store.initialize()
                assert snapshot(conn) == before
                assert store.identity() == identity
            print(
                json.dumps(
                    {
                        "six_tables_preserved": True,
                        "repeated_initialize_preserved": True,
                        "snapshot_sha256": hashlib.sha256(args.snapshot.read_bytes()).hexdigest(),
                        "module": __import__("tushare_downloader").__file__,
                    }
                )
            )


if __name__ == "__main__":
    main()
