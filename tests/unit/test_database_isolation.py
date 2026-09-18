"""Misconfigured test entry points must fail before any database mutation."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def load(relative):
    spec = importlib.util.spec_from_file_location(
        "guard_fixture", Path(__file__).parents[2] / relative
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("entry", ["test", "benchmark"])
@pytest.mark.parametrize("identity", [None, ("wrong", "expected"), ("expected", "wrong")])
def test_database_entry_refuses_missing_or_wrong_identity(monkeypatch, tmp_path, entry, identity):
    module = load("tests/integration/conftest.py" if entry == "test" else "benchmarks/run.py")
    key = "TEST_DATABASE_URL" if entry == "test" else "BENCH_DATABASE_URL"
    expected = "tushare_test" if entry == "test" else "tushare_bench"
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"{key}=must-not-use-dotenv\nPGDATABASE=production\n")
    calls = []

    class Connection:
        info = SimpleNamespace(dbname="wrong", user="wrong")

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, *args, **kwargs):
            pytest.fail("Rejected identity executed SQL")

    def connect(dsn, **kwargs):
        calls.append(dsn)
        assert identity is not None, "Missing process setting attempted a connection"
        conn = Connection()
        conn.info = SimpleNamespace(
            **dict(
                zip(
                    ("dbname", "user"),
                    (expected if value == "expected" else value for value in identity),
                    strict=True,
                )
            )
        )
        return conn

    monkeypatch.setattr(module.psycopg, "connect", connect)
    if identity is None:
        monkeypatch.delenv(key, raising=False)
    else:
        monkeypatch.setenv(key, "explicit-fixture-dsn")
    with pytest.raises(pytest.fail.Exception if entry == "test" else ValueError):
        if entry == "test":
            next(module.db.__wrapped__())
        else:
            module.run(
                SimpleNamespace(mode="database", repeat=5, rows=1, output=tmp_path / "results")
            )
    assert calls == ([] if identity is None else ["explicit-fixture-dsn"])
