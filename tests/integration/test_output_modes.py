"""The terminal presentation must not change request or storage semantics."""

import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from psycopg import sql
from test_download import config

from tushare_downloader.apis import get_api
from tushare_downloader.client import ApiResult, RequestError
from tushare_downloader.download import execute

pytestmark = pytest.mark.integration


class Terminal(io.StringIO):
    def isatty(self):
        return True


@pytest.mark.parametrize(
    "api_name", ["daily_basic", "daily", "adj_factor", "stk_limit", "suspend_d"]
)
@pytest.mark.parametrize("scenario", ["success", "empty", "partial"])
def test_six_modes_preserve_requests_database_and_report(
    db, tmp_path, monkeypatch, scenario, api_name
):
    API = get_api(api_name)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    identity = db.initialize()
    expected = None
    for plain in (False, True):
        for level in ("quiet", "normal", "verbose"):
            db.clean(API, apply=True, database="tushare_test", database_id=identity)
            folder = tmp_path / f"{plain}-{level}"
            settings = replace(config(folder), plain=plain)
            calls = []

            class Client:
                attempts = 0

                def __init__(self, *a, **kw):
                    self.callback = kw["on_attempt"]

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

                def query(self, api, params):
                    self.attempts += 1
                    self.callback(api.name, 1)
                    calls.append(params)
                    if scenario == "partial" and len(calls) == 2:
                        raise RequestError("network", "simulated failure")
                    if scenario == "empty":
                        return ApiResult((), 0, 0, 1)
                    day = date(2024, 1, len(calls) + 1)
                    values = (
                        "000001.SZ",
                        day,
                        *(
                            Decimal("1")
                            if f.kind == "decimal"
                            else None
                            if f.name == "suspend_timing"
                            else "S"
                            for f in API.fields[2:]
                        ),
                    )
                    return ApiResult((values,), 1, 0, 1)

            stdout, stderr = Terminal(), Terminal()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = execute(
                    db,
                    API,
                    "fetch",
                    settings,
                    start=date(2024, 1, 2),
                    end=date(2024, 1, 3),
                    quiet=level == "quiet",
                    verbose=int(level == "verbose"),
                    client_factory=Client,
                )
            report = next(settings.report_dir.glob("*/report.md")).read_text()
            semantic = "\n".join(
                line
                for line in report.split("## Logs")[0].splitlines()
                if not line.startswith(("| Started (UTC)", "| Report updated (UTC)", "| Log |"))
            )
            source_rows = db.conn.execute(
                sql.SQL("SELECT {}, _is_stale FROM {} ORDER BY trade_date").format(
                    sql.SQL(",").join(map(sql.Identifier, API.field_names)),
                    sql.Identifier("raw", API.name),
                )
            ).fetchall()
            observed = (code, calls, source_rows, semantic)
            if expected is None:
                expected = observed
            else:
                assert observed == expected
            combined = stdout.getvalue() + stderr.getvalue()
            assert stdout.getvalue().startswith("Log: ")
            assert "Report:" in combined
            if plain:
                assert not any(control in combined for control in ("\x1b", "\r"))
            if level == "quiet":
                assert "Inserted:" not in stdout.getvalue()
            if scenario == "partial":
                assert "simulated failure" in stderr.getvalue()

            if scenario == "empty" and api_name == "suspend_d":
                assert "Empty response may indicate no suspension/resumption records." in report
                assert "missing keys were not reconciled" in report
