"""Connection validation shared by native setup and compatibility helpers."""

import re

from .config import Settings, duration


def connection_errors(values, reader, administrator=None):
    errors = {}
    host = values.get("PGHOST", "localhost")
    if not host or "," in host or any(ord(char) < 32 for char in host):
        errors["host"] = "Enter one server host without control characters."
    try:
        if not 1 <= int(values.get("PGPORT", "5432")) <= 65535:
            raise ValueError()
    except (ValueError, TypeError):
        errors["port"] = "Enter an integer port from 1 to 65535."
    for field, value in (
        ("database", values.get("PGDATABASE", "tushare")),
        ("writer", values.get("PGUSER", "tushare_writer")),
        ("reader", reader),
    ):
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", value):
            errors[field] = (
                "Use 1–63 lowercase letters, digits or underscores; start with a letter or underscore."
            )
    if values.get("PGSSLMODE", "prefer") not in {
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    }:
        errors["sslmode"] = "Choose disable, allow, prefer, require, verify-ca or verify-full."
    if reader == values.get("PGUSER", "tushare_writer"):
        errors["reader"] = "Reader and writer must be different accounts."
    if administrator:
        for field, key, default in (
            ("admin_user", "user", ""),
            ("maintenance", "maintenance_database", "postgres"),
        ):
            if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", administrator.get(key, default)):
                errors[field] = "Use a valid lowercase PostgreSQL name (1–63 characters)."
    return errors


def selected_settings(values):
    cfg = Settings(
        pg_host=values.get("PGHOST", "localhost"),
        pg_port=int(values.get("PGPORT", "5432")),
        pg_database=values.get("PGDATABASE", "tushare"),
        pg_user=values.get("PGUSER", "tushare_writer"),
        pg_password=values.get("PGPASSWORD", ""),
        pg_sslmode=values.get("PGSSLMODE", "prefer"),
        connect_timeout=int(values.get("CONNECT_TIMEOUT_SECONDS", "10")),
        inspect_timeout=duration(values.get("INSPECT_TIMEOUT", "5s"), allow_zero=False),
        setup_step_timeout=duration(values.get("SETUP_STEP_TIMEOUT", "60s"), allow_zero=False),
    )
    if not 1 <= cfg.pg_port <= 65535 or cfg.connect_timeout < 1:
        raise ValueError("Invalid port or connection timeout.")
    if cfg.inspect_timeout.total_seconds() > 300 or cfg.setup_step_timeout.total_seconds() > 600:
        raise ValueError("Inspection/setup time budget exceeds its allowed maximum.")
    if cfg.pg_sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
        raise ValueError("Invalid PGSSLMODE.")
    if "," in cfg.pg_host or not cfg.pg_host or any(ord(c) < 32 for c in cfg.pg_host):
        raise ValueError("Setup requires one host without control characters.")
    return cfg
