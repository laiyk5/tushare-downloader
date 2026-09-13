"""Read configuration without importing credentials or opening connections."""

import os
import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


class ConfigError(ValueError):
    """An invalid configuration key, with no secret value in its message."""


def duration(value: str, *, allow_zero: bool = True) -> timedelta:
    """Parse explicit seconds/minutes/hours/days; bare 0 means force."""
    if value == "0" and allow_zero:
        return timedelta(0)
    match = re.fullmatch(r"(\d+)(s|m|h|d)", value.strip())
    if not match:
        raise ConfigError("时长格式应为 30s、5m、24h、7d 或 0。")
    seconds = int(match[1]) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[match[2]]
    if seconds == 0 and not allow_zero:
        raise ConfigError("时长必须大于零。")
    try:
        return timedelta(seconds=seconds)
    except OverflowError:
        raise ConfigError("时长超出支持范围。") from None


@dataclass(frozen=True)
class Settings:
    token: str = field(default="", repr=False)
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "tushare"
    pg_user: str = "tushare_writer"
    pg_password: str = field(default="", repr=False)
    pg_sslmode: str = "prefer"
    log_dir: Path = Path("logs")
    report_dir: Path = Path("reports")
    log_level: str = "INFO"
    progress: str = "auto"
    plain: bool = False
    progress_interval: int = 5
    report_max_items: int = 20
    max_age: timedelta = timedelta(hours=24)
    lookback_days: int = 7
    empty_recheck_age: timedelta = timedelta(hours=24)
    max_attempts: int = 4
    max_consecutive_failed_slices: int = 10
    requests_per_minute: int = 60
    connect_timeout: int = 10
    read_timeout: int = 60
    retry_max_seconds: int = 60
    max_response_bytes: int = 32 * 1024 * 1024

    def require_token(self) -> str:
        if not self.token:
            raise ConfigError("实际请求需要配置 TUSHARE_TOKEN。")
        return self.token


def load_settings(
    env_file: Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    plain: bool = False,
) -> Settings:
    """CLI plain > environment > selected file > defaults; no parent search."""
    base = (cwd or Path.cwd()).resolve()
    selected = env_file or Path(".env")
    selected = selected if selected.is_absolute() else base / selected
    if env_file is not None and not selected.is_file():
        raise ConfigError("指定的配置文件不存在或不是普通文件。")
    try:
        values = (
            {
                key: value
                for key, value in dotenv_values(selected, interpolate=False).items()
                if value is not None
            }
            if selected.is_file()
            else {}
        )
    except (OSError, UnicodeError):
        raise ConfigError("无法读取配置文件。") from None
    values.update(os.environ if environ is None else environ)

    def integer(key: str, default: int, minimum: int = 1, maximum: int | None = None) -> int:
        try:
            result = int(values.get(key, str(default)))
        except ValueError:
            raise ConfigError(f"{key} 必须为整数。") from None
        if result < minimum or (maximum is not None and result > maximum):
            raise ConfigError(f"{key} 超出允许范围。")
        return result

    def choice(key: str, default: str, allowed: set[str]) -> str:
        value = values.get(key, default)
        if value not in allowed:
            raise ConfigError(f"{key} 的取值无效。")
        return value

    def time_value(key: str, default: str, allow_zero: bool = True) -> timedelta:
        try:
            return duration(values.get(key, default), allow_zero=allow_zero)
        except ConfigError:
            raise ConfigError(f"{key} 的时长无效。") from None

    def directory(key: str, default: str) -> Path:
        path = Path(values.get(key, default))
        return (path if path.is_absolute() else base / path).resolve()

    plain_value = choice("PLAIN", "false", {"true", "false", "1", "0"})
    return Settings(
        token=values.get("TUSHARE_TOKEN", ""),
        pg_host=values.get("PGHOST", "localhost"),
        pg_port=integer("PGPORT", 5432, maximum=65535),
        pg_database=values.get("PGDATABASE", "tushare"),
        pg_user=values.get("PGUSER", "tushare_writer"),
        pg_password=values.get("PGPASSWORD", ""),
        pg_sslmode=choice(
            "PGSSLMODE",
            "prefer",
            {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"},
        ),
        log_dir=directory("LOG_DIR", "logs"),
        report_dir=directory("REPORT_DIR", "reports"),
        log_level=choice("LOG_LEVEL", "INFO", {"DEBUG", "INFO", "WARNING", "ERROR"}),
        progress=choice("PROGRESS", "auto", {"auto", "off"}),
        plain=plain or plain_value in {"true", "1"} or "NO_COLOR" in values,
        progress_interval=integer("PROGRESS_INTERVAL_SECONDS", 5, maximum=60),
        report_max_items=integer("REPORT_MAX_ITEMS", 20),
        max_age=time_value("MAX_AGE", "24h"),
        lookback_days=integer("LOOKBACK_DAYS", 7),
        empty_recheck_age=time_value("EMPTY_RECHECK_AGE", "24h", False),
        max_attempts=integer("MAX_ATTEMPTS", 4),
        max_consecutive_failed_slices=integer("MAX_CONSECUTIVE_FAILED_SLICES", 10, 0),
        requests_per_minute=integer("REQUESTS_PER_MINUTE", 60),
        connect_timeout=integer("CONNECT_TIMEOUT_SECONDS", 10),
        read_timeout=integer("READ_TIMEOUT_SECONDS", 60),
        retry_max_seconds=integer("RETRY_MAX_SECONDS", 60),
        max_response_bytes=integer("MAX_RESPONSE_BYTES", 32 * 1024 * 1024),
    )
