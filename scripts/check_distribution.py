import json
import os
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
wheel = root / "dist/tushare_downloader-0.2.0-py3-none-any.whl"
sdist = root / "dist/tushare_downloader-0.2.0.tar.gz"
with zipfile.ZipFile(wheel) as archive:
    files = archive.namelist()
    metadata = archive.read("tushare_downloader-0.2.0.dist-info/METADATA").decode()
    license_text = archive.read("tushare_downloader-0.2.0.dist-info/licenses/LICENSE").decode()
    assert license_text == (root / "LICENSE").read_text()
    assert "License-Expression: MIT" in metadata and "Version: 0.2.0" in metadata
    assert all(
        p.startswith(("tushare_downloader/", "tushare_downloader-0.2.0.dist-info/")) for p in files
    )
    assert not any(p.endswith((".so", ".dll", ".env", ".jsonl")) for p in files)
with tarfile.open(sdist) as archive:
    names = archive.getnames()
    assert archive.extractfile("tushare_downloader-0.2.0/LICENSE").read().decode() == license_text
    assert not any("/.env" in p or "/logs/" in p or "/reports/" in p for p in names)
    print("sdist files:", json.dumps(names))
with tempfile.TemporaryDirectory(prefix="td-v02-wheel-") as temporary:
    folder = Path(temporary)
    venv = folder / "venv"
    subprocess.run(["uv", "venv", str(venv), "--python", "3.12"], check=True)
    subprocess.run(
        ["uv", "pip", "install", "--python", str(venv / "bin/python"), str(wheel)], check=True
    )
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if not any(x in k for x in ("TOKEN", "DATABASE", "PYTHONPATH", "VIRTUAL_ENV"))
    }
    for args in (["--help"], ["--version"], ["list"]):
        result = subprocess.run(
            [str(venv / "bin/tushare-downloader"), *args],
            cwd=folder,
            env=clean_env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        if args == ["--version"]:
            assert "0.2.0" in result.stdout
        if args == ["list"]:
            assert "daily_basic" in result.stdout and "stock_basic" in result.stdout
        print(json.dumps({"args": args, "exit_code": result.returncode, "stdout": result.stdout}))
print("Wheel and sdist license and isolation checks passed.")
