"""Restricted, ephemeral setup credentials; no configuration persistence."""

import json
import os
import stat

from .setup_db import name


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate credential key.")
        result[key] = value
    return result


def load_credentials(path):
    """Read a bounded regular file using the opened descriptor's identity."""
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or info.st_size > 65536
        ):
            raise ValueError("Credentials require a private, owned regular file (max 65536 bytes).")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("Credential file exceeds 65536 bytes.")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("Cannot read a valid private credential file.") from None
    finally:
        if fd is not None:
            os.close(fd)
    if not isinstance(value, dict) or set(value) - {"version", "admin", "writer", "reader"}:
        raise ValueError("Unsupported credential structure.")
    if type(value.get("version")) is not int or value["version"] != 1:
        raise ValueError("Credential version must be integer 1.")
    for role in ("admin", "writer", "reader"):
        if role not in value:
            continue
        entry = value[role]
        allowed = (
            {"user", "maintenance_database", "password"}
            if role == "admin"
            else {"password", "allow_passwordless_creation"}
        )
        if not isinstance(entry, dict) or set(entry) - allowed:
            raise ValueError("Unsupported credential account structure.")
        for key, item in entry.items():
            expected = bool if key == "allow_passwordless_creation" else str
            if type(item) is not expected:
                raise ValueError("Invalid credential field type.")
        if role == "admin":
            name(entry.get("user", ""))
            name(entry.setdefault("maintenance_database", "postgres"))
        elif entry.get("password") and entry.get("allow_passwordless_creation"):
            raise ValueError("Password and passwordless creation are mutually exclusive.")
    return value


def writer_password(credentials, existing):
    entry = credentials.get("writer", {})
    password = entry.get("password") or existing
    if password and entry.get("allow_passwordless_creation"):
        raise ValueError("Password and passwordless creation are mutually exclusive.")
    return password
