"""Inspect cost on synthetic data in the explicitly disposable benchmark database."""

import json
import os
import time
from datetime import timedelta
from pathlib import Path

import psycopg

from tushare_downloader.config import Settings
from tushare_downloader.inspection import inspect_dataset
from tushare_downloader.storage import Store


def main():
    dsn = os.environ["BENCH_DATABASE_URL"]
    samples = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        if (conn.info.user, conn.info.dbname) != ("tushare_bench", "tushare_bench"):
            raise ValueError("Benchmark requires dedicated tushare_bench role and database.")
        store = Store(conn)
        with store.writer():
            store.initialize()
        cfg = Settings(
            pg_host=conn.info.host,
            pg_port=conn.info.port,
            pg_database=conn.info.dbname,
            pg_user=conn.info.user,
            inspect_timeout=timedelta(seconds=5),
        )
        for count in [1000, 100000]:
            conn.execute("TRUNCATE raw.daily")
            conn.execute(
                "INSERT INTO raw.daily(ts_code,trade_date,_is_stale,_last_seen_at,_updated_at) "
                "SELECT 'SYNTHETIC_'||i, DATE '2020-01-01'+(i %% 1820),false,now(),now() "
                "FROM generate_series(1,%s) i",
                (count,),
            )
            conn.execute("ANALYZE raw.daily")
            for stale in [False, True]:
                if stale:
                    conn.execute(
                        "UPDATE raw.daily SET _is_stale=true WHERE trade_date>DATE '2020-01-10'"
                    )
                for counts in [False, True]:
                    for repeat in range(5):
                        start = time.perf_counter()
                        result = inspect_dataset(cfg, "daily", counts)
                        samples.append(
                            dict(
                                rows=count,
                                stale_dense=stale,
                                counts=counts,
                                repeat=repeat,
                                seconds=time.perf_counter() - start,
                                ok=result["ok"],
                            )
                        )
                        if not result["ok"]:
                            raise ValueError("Inspection failed in benchmark.")
            plans = conn.execute(
                "EXPLAIN (FORMAT JSON) SELECT max(trade_date) FROM raw.daily WHERE NOT _is_stale"
            ).fetchone()[0]
        destination = Path("/tmp/r2-inspect-benchmark.json")
        destination.write_text(json.dumps({"samples": samples, "last_query_plan": plans}, indent=2))
        print(str(destination))


if __name__ == "__main__":
    main()
