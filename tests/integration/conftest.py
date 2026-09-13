"""Integration tests require an explicitly configured, isolated database."""

import os

import psycopg
import pytest

from tushare_downloader.storage import Store


@pytest.fixture
def db():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.fail(
            "Set TEST_DATABASE_URL to a dedicated tushare_test database; no production fallback."
        )
    conn = psycopg.connect(dsn, autocommit=True)
    if conn.info.dbname != "tushare_test" or conn.info.user != "tushare_test":
        conn.close()
        pytest.fail("Integration tests require database AND user tushare_test.")
    with conn:
        # This dedicated test database is explicitly disposable.
        conn.execute("DROP SCHEMA IF EXISTS raw CASCADE")
        conn.execute("DROP SCHEMA IF EXISTS meta CASCADE")
        yield Store(conn)
