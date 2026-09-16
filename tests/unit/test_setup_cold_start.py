"""Exercise native Textual capture in a fresh interpreter, before any spawn worker."""

import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(os.name != "posix", reason="POSIX multiprocessing descriptor regression")
@pytest.mark.parametrize("crash", [False, True], ids=["worker", "ui-error"])
def test_setup_first_worker_under_textual_capture(tmp_path, crash):
    script = r"""
import asyncio
import sys
from pathlib import Path
import click
from tushare_downloader import setup_tui
from tushare_downloader.bounded import bounded

class ColdStartApp(setup_tui.SetupApp):
    async def on_mount(self):
        assert sys.stderr.fileno() == -1
        value = await asyncio.to_thread(bounded, abs, -7, seconds=3)
        assert value == 7
        Path("worker-ok").write_text("7")
        if sys.argv[1] == "crash":
            raise RuntimeError("controlled UI failure")
        self.exit(0)

    def run(self):
        return super().run(headless=True)

setup_tui.SetupApp = ColdStartApp
ctx = click.Context(click.Command("setup"), obj={"env_file": str(Path("missing.env"))})
try:
    setup_tui.run_tui(ctx)
except click.exceptions.Exit as result:
    raise SystemExit(result.exit_code)
"""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PG", "SETUP_", "TUSHARE_"))
        and key not in {"PLAIN", "LOG_DIR", "DATABASE_URL"}
    }
    result = subprocess.run(
        [sys.executable, "-c", script, "crash" if crash else "ok"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == (1 if crash else 0), result.stdout + result.stderr
    assert (tmp_path / "worker-ok").read_text() == "7"
    assert "bad value(s) in fds_to_keep" not in result.stderr
