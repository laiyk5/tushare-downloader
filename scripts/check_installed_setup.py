"""Offline wheel installation smoke check in a temporary isolated environment."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="td-installed-") as folder:
    root = Path(folder)
    python = root / "venv/bin/python"
    subprocess.run(["uv", "venv", str(root / "venv")], check=True)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--offline",
            "--python",
            str(python),
            str(repo / "dist/tushare_downloader-0.4.0-py3-none-any.whl"),
        ],
        check=True,
    )
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PG", "SETUP_"))
        and k not in {"DATABASE_URL", "PYTHONPATH", "VIRTUAL_ENV"}
    }
    cli = root / "venv/bin/tushare-downloader"
    results = []
    for args, expected in [
        (["--help"], 0),
        (["setup", "--help"], 0),
        (["setup", "--headless"], 4),
        (["setup"], 2),
    ]:
        result = subprocess.run(
            [str(cli), *args],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
        assert result.returncode == expected, (
            args,
            result.returncode,
            result.stdout,
            result.stderr,
        )
        results.append(
            {
                "args": args,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    imported = subprocess.run(
        [
            str(python),
            "-c",
            'import tushare_downloader,sys; print(tushare_downloader.__file__); import tushare_downloader.cli; assert "textual" not in sys.modules',
        ],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert str(repo / "src") not in imported.stdout
    assert not (root / ".env").exists()
    print(json.dumps(results, indent=2))
    print(
        "Installed wheel: help, setup help, read-only headless missing config, non-TTY rejection, lazy Textual import passed."
    )
