import fcntl
import json
import os
import pty
import select
import signal
import struct
import subprocess
import tempfile
import termios
import time
from pathlib import Path

root = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
child = """from types import SimpleNamespace
import click,termios
from tushare_downloader.setup_dialogue import Dialogue
d=Dialogue(SimpleNamespace(obj={}))
try:
    d.ask('Synthetic password',secret=True)
except (click.Abort,KeyboardInterrupt):
    pass
assert termios.tcgetattr(0)[3] & termios.ECHO
print('ECHO_RESTORED',flush=True)
"""
results = []
for mode in ("enter", "interrupt", "eof"):
    pid, fd = pty.fork()
    if pid == 0:
        os.execv(str(root / ".venv/bin/python"), [str(root / ".venv/bin/python"), "-c", child])
    data = b""
    sent = False
    done = False
    deadline = time.monotonic() + 10
    try:
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    data += os.read(fd, 65536)
                except OSError:
                    break
            if not sent and b">:" in data and not (termios.tcgetattr(fd)[3] & termios.ECHO):
                assert not termios.tcgetattr(fd)[3] & termios.ECHO
                os.write(
                    fd,
                    {"enter": b"FAKE_SECRET_ONLY_742\n", "interrupt": b"\x03", "eof": b"\x04"}[
                        mode
                    ],
                )
                sent = True
            if b"ECHO_RESTORED" in data:
                done = True
                break
        assert sent and done, (mode, data)
        assert b"FAKE_SECRET_ONLY_742" not in data
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0
    finally:
        if not done:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(fd)
    results.append(dict(case=mode, hidden=True, echo_restored=True))

with tempfile.TemporaryDirectory() as folder:
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("PG", "TUSHARE", "SETUP"))
        and k not in ("DATABASE_URL", "NO_COLOR", "TERM", "COLUMNS")
    }
    env["TERM"] = "xterm-256color"
    cli = str(root / ".venv/bin/tushare-downloader")
    for width in (40, 80, 120):
        for args in (["--help"], ["schema", "daily"]):
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 10, width, 0, 0))
            proc = subprocess.Popen(
                [cli, *args], cwd=folder, env=env, stdin=slave, stdout=slave, stderr=slave
            )
            os.close(slave)
            data = b""
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        data += os.read(master, 65536)
                    except OSError:
                        break
            assert proc.wait(timeout=2) == 0
            os.close(master)
            assert b"Examples:" in data if args == ["--help"] else b"ts_code" in data
            results.append(dict(case="native_pty", width=width, height=10, args=args, passed=True))
    for extra, args in (
        ({}, ["--help"]),
        ({"TERM": "dumb"}, ["--help"]),
        ({"NO_COLOR": "1"}, ["--help"]),
        ({}, ["--plain", "--help"]),
    ):
        out = subprocess.run(
            [cli, *args], cwd=folder, env=env | extra, capture_output=True, timeout=10
        )
        assert (
            out.returncode == 0
            and b"\x1b" not in out.stdout + out.stderr
            and b"\r" not in out.stdout + out.stderr
        )
        results.append(dict(case="pipe_plain", environment=extra, args=args, passed=True))
print(json.dumps(results, indent=2))
