"""Fresh interpreter coverage for the sequential setup process boundary."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("crash", [False, True], ids=["worker", "internal-error"])
def test_setup_first_worker_in_fresh_interpreter(tmp_path, crash):
    script = r"""
import sys
from pathlib import Path
from tushare_downloader import cli, setup_dialogue
from tushare_downloader.bounded import bounded
from tushare_downloader.setup_service import SetupSession

class Backend:
    def inspect(self, *args):
        assert bounded(abs, -7, seconds=3) == 7
        Path("worker-ok").write_text("7")
        if sys.argv[1] == "crash":
            raise ZeroDivisionError("SECRET internal failure")
        return dict(kind="managed", roles_safe=True, writer_exists=True,
                    reader_exists=True, grants_needed=False, missing=[],
                    database_id="fixture")
cli.setup_terminal_available = lambda: True
setup_dialogue.SetupSession = lambda *a, **kw: SetupSession(*a, **kw, backend=Backend())
Path(".env").write_text("PGHOST=localhost\nPGDATABASE=fixture\nPGUSER=writer\n")
cli.main(["--plain", "setup"])
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
    assert "SECRET" not in result.stdout + result.stderr
