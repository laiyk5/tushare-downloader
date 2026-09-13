"""Explicit API registry and field schemas, without database/network side effects."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from types import MappingProxyType
from typing import Literal
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Field:
    name: str
    kind: Literal["text", "date", "decimal"]
    nullable: bool = True


@dataclass(frozen=True)
class ApiSpec:
    name: str
    fields: tuple[Field, ...]
    unique_key: tuple[str, ...]
    change_kind: Literal["append-only", "mutable"]
    query_kind: Literal["time-range", "snapshot"]
    parameter_names: frozenset[str]
    spec_version: str = "1"
    block_origin: date = date(1970, 1, 1)
    block_days: int = 1
    requests_per_minute: int | None = None
    row_limit: int = 6000
    stale_scope_verified: bool = False

    def __post_init__(self) -> None:
        names = [field.name for field in self.fields]
        if self.block_days < 1 or len(names) != len(set(names)):
            raise ValueError("Invalid API block size or duplicate fields")
        if not self.unique_key or not set(self.unique_key) <= set(names):
            raise ValueError("API must have an explicit field-based unique key")
        if any(field.nullable for field in self.fields if field.name in self.unique_key):
            raise ValueError("Unique-key fields cannot be nullable")

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)

    def available_end(self, now: datetime) -> date:
        if self.query_kind != "time-range":
            raise ValueError("Snapshot has no date boundary")
        if now.utcoffset() is None:
            raise ValueError("Timezone-aware timestamp required")
        return now.astimezone(ZoneInfo("Asia/Shanghai")).date() - timedelta(days=1)


# Imports stay local to the registry definitions to keep specs in separate files.
from .daily_basic import DAILY_BASIC  # noqa: E402
from .stock_basic import STOCK_BASIC  # noqa: E402

APIS = MappingProxyType({spec.name: spec for spec in (DAILY_BASIC, STOCK_BASIC)})


def get_api(name: str) -> ApiSpec:
    try:
        return APIS[name]
    except KeyError:
        raise ValueError(f"不支持的 API：{name}") from None
