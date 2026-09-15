import json
import os
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
wheel = root / f"dist/tushare_downloader-{version}-py3-none-any.whl"
sdist = root / f"dist/tushare_downloader-{version}.tar.gz"
with zipfile.ZipFile(wheel) as archive:
    files = archive.namelist()
    metadata = archive.read(f"tushare_downloader-{version}.dist-info/METADATA").decode()
    license_text = archive.read(f"tushare_downloader-{version}.dist-info/licenses/LICENSE").decode()
    assert license_text == (root / "LICENSE").read_text()
    assert "License-Expression: MIT" in metadata and f"Version: {version}" in metadata
    assert all(
        p.startswith(("tushare_downloader/", f"tushare_downloader-{version}.dist-info/"))
        for p in files
    )
    assert not any(p.endswith((".so", ".dll", ".env", ".jsonl")) for p in files)
with tarfile.open(sdist) as archive:
    names = archive.getnames()
    assert (
        archive.extractfile(f"tushare_downloader-{version}/LICENSE").read().decode() == license_text
    )
    assert not any("/.env" in p or "/logs/" in p or "/reports/" in p for p in names)
    print("sdist files:", json.dumps(names))
with tempfile.TemporaryDirectory(prefix="td-wheel-") as temporary:
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
            assert version in result.stdout
        if args == ["list"]:
            assert all(
                name in result.stdout
                for name in (
                    "daily_basic",
                    "stock_basic",
                    "daily",
                    "adj_factor",
                    "stk_limit",
                    "suspend_d",
                )
            )
        print(json.dumps({"args": args, "exit_code": result.returncode, "stdout": result.stdout}))
print("Wheel and sdist license and isolation checks passed.")
