"""Conservative dotenv updates, with optimistic concurrency and private atomic files."""

import os
import re
import tempfile
from io import StringIO
from pathlib import Path

from dotenv.parser import parse_stream

KEYS = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE")


def read_config(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Configuration must be a regular file, not a symlink.")
    if not path.exists():
        return None, {}
    original = path.read_bytes()
    try:
        content = original.decode("utf-8")
    except UnicodeError:
        raise ValueError("Configuration is not UTF-8.") from None
    values = {}
    for binding in parse_stream(StringIO(content)):
        if binding.error:
            raise ValueError("Configuration syntax is ambiguous; select a new file or fix it.")
        if binding.key in KEYS:
            if binding.key in values or (binding.value and any(c in binding.value for c in "\r\n")):
                raise ValueError("Duplicate or multiline connection key; no changes made.")
        if binding.key:
            values[binding.key] = binding.value or ""
    return original, values


def quote(value):
    value = str(value)
    if any(ord(c) < 32 for c in value):
        raise ValueError("Connection values must not contain control characters.")
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def save_config(path, original, updates):
    path = Path(path)
    if set(updates) - set(KEYS):
        raise ValueError("Only database connection keys may be saved.")
    current, _ = read_config(path)
    if current != original:
        raise ValueError("Configuration changed since inspection; review it again.")
    text = current.decode("utf-8") if current is not None else "# Database\n"
    lines = text.splitlines(keepends=True)
    remaining = dict(updates)
    for i, line in enumerate(lines):
        match = re.match(r"^(\s*(?:export\s+)?)([A-Z_]+)\s*=", line)
        if match and match[2] in remaining:
            # Preserve comments outside quoted values.
            tail = line[match.end() :].rstrip("\r\n")
            escaped = False
            delim = None
            comment = ""
            for j, char in enumerate(tail):
                if escaped:
                    escaped = False
                elif char == "\\" and delim:
                    escaped = True
                elif delim:
                    if char == delim:
                        delim = None
                elif char in "\"'":
                    delim = char
                elif char == "#" and (j == 0 or tail[j - 1].isspace()):
                    comment = " " + tail[j:]
                    break
            ending = "\r\n" if line.endswith("\r\n") else "\n"
            lines[i] = f"{match[1]}{match[2]}={quote(remaining.pop(match[2]))}{comment}{ending}"
    result = "".join(lines)
    if remaining:
        if result and not result.endswith("\n"):
            result += "\n"
        result += "# Database connection settings\n"
        result += "".join(f"{k}={quote(v)}\n" for k, v in remaining.items())
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".setup-", dir=path.parent)
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(result.encode("utf-8"))
            output.flush()
            os.fsync(output.fileno())
        if read_config(path)[0] != original:
            raise ValueError("Configuration changed before replacement; no overwrite performed.")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
