"""Bounded Tushare HTTP transport and typed response parsing."""

import json
import random
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Callable

import requests

from .apis import ApiSpec, Field
from .config import Settings

API_URL = "https://api.tushare.pro"


class RequestError(Exception):
    """Safe request diagnostic; never holds the original request or credentials."""

    def __init__(self, category: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.category = category
        self.retryable = retryable


@dataclass(frozen=True)
class ApiResult:
    rows: tuple[tuple[object, ...], ...]
    received_rows: int
    duplicate_rows: int
    attempts: int


def _value(value: object, field: Field) -> object:
    if value is None or (value == "" and field.kind == "date" and field.nullable):
        if not field.nullable:
            raise ValueError("Required field is null")
        return None
    if field.kind == "text":
        if not isinstance(value, str):
            raise ValueError("Text required")
        return value
    if field.kind == "date":
        if (
            not isinstance(value, str)
            or len(value) != 8
            or not value.isascii()
            or not value.isdigit()
        ):
            raise ValueError("YYYYMMDD required")
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("Decimal required")
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError("Non-finite number")
    return number


def parse_rows(data: object, api: ApiSpec) -> tuple[tuple[tuple[object, ...], ...], int, int]:
    if not isinstance(data, dict):
        raise RequestError("protocol", "API data 结构无效。")
    names, items = data.get("fields"), data.get("items")
    if (
        not isinstance(names, list)
        or not all(isinstance(name, str) for name in names)
        or len(names) != len(set(names))
        or not isinstance(items, list)
        or set(names) != set(api.field_names)
    ):
        raise RequestError("protocol", "API 字段或行集合与请求不一致。")
    positions = [names.index(name) for name in api.field_names]
    key_positions = [api.field_names.index(name) for name in api.unique_key]
    by_key = {}
    duplicates = 0
    for item in items:
        if not isinstance(item, list) or len(item) != len(names):
            raise RequestError("protocol", "API 返回行宽与字段数不一致。")
        try:
            row = tuple(_value(item[pos], field) for field, pos in zip(api.fields, positions))
        except (ValueError, InvalidOperation, TypeError, OverflowError):
            raise RequestError("type", "API 返回值不符合字段类型。") from None
        key = tuple(row[pos] for pos in key_positions)
        if key in by_key:
            if by_key[key] != row:
                raise RequestError("duplicate_conflict", "同一响应内出现同键不同值。")
            duplicates += 1
        else:
            by_key[key] = row
    return tuple(by_key.values()), len(items), duplicates


def _reject_constant(value: str):
    raise ValueError("Non-standard JSON number")


class TushareClient:
    """One retry layer and one pacing clock shared by all calls on this client."""

    def __init__(
        self,
        settings: Settings,
        *,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        jitter: Callable[[], float] = random.random,
        on_retry: Callable[[str, int, float], None] | None = None,
        on_attempt: Callable[[str, int], None] | None = None,
        on_phase: Callable[[str], None] | None = None,
    ):
        self._token = settings.require_token()
        self.settings = settings
        self.session = session if session is not None else requests.Session()
        self._owned_session = session is None
        self.clock, self.sleep, self.wall_clock = clock, sleep, wall_clock
        self.jitter, self.on_retry = jitter, on_retry
        self._last_attempt: float | None = None
        self._started = clock()
        self.attempts = 0
        self.on_attempt = on_attempt
        self.on_phase = on_phase or (lambda stage: None)
        self.timings = dict(
            http_seconds=0.0, parse_seconds=0.0, pacing_seconds=0.0, retry_seconds=0.0
        )
        self.response_bytes = 0

    def close(self) -> None:
        if self._owned_session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _pace(self, api: ApiSpec) -> None:
        rate = min(
            self.settings.requests_per_minute,
            api.requests_per_minute or self.settings.requests_per_minute,
        )
        interval = 60 / rate
        previous = self._started if self._last_attempt is None else self._last_attempt
        remaining = previous + interval - self.clock()
        if remaining > 0:
            self.on_phase("限速等待")
            before_wait = self.clock()
            self.sleep(remaining)
            self.timings["pacing_seconds"] += self.clock() - before_wait
        self._last_attempt = self.clock()

    def _retry_after(self, header: str | None) -> float:
        if not header:
            return 0
        try:
            if header.isdigit():
                wait = float(header)
            else:
                parsed = parsedate_to_datetime(header)
                if parsed.utcoffset() is None:
                    return 0
                wait = max(0, (parsed - self.wall_clock()).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 0
        if wait > self.settings.retry_max_seconds:
            raise RequestError("retry_deferred", "服务端要求的等待时间超过本次允许预算。")
        return wait

    def query(self, api: ApiSpec, params: dict[str, str]) -> ApiResult:
        if not set(params) <= api.parameter_names or any(
            not isinstance(v, str) for v in params.values()
        ):
            raise RequestError("parameters", "请求参数不在接口白名单内或类型无效。")
        payload = {
            "api_name": api.name,
            "token": self._token,
            "params": dict(params),
            "fields": ",".join(api.field_names),
        }
        for attempt in range(1, self.settings.max_attempts + 1):
            wait = 0.0
            self._pace(api)
            self.attempts += 1
            if self.on_attempt:
                self.on_attempt(api.name, attempt)
            response = None
            self.on_phase("HTTP 请求")
            http_started, parse_started = self.clock(), None
            try:
                response = self.session.post(
                    API_URL,
                    json=payload,
                    timeout=(self.settings.connect_timeout, self.settings.read_timeout),
                    allow_redirects=False,
                    stream=True,
                )
                status = response.status_code
                if status == 429 or 500 <= status < 600:
                    wait = self._retry_after(response.headers.get("Retry-After"))
                    raise RequestError(
                        "http_transient", f"HTTP {status}，暂时无法取得数据。", retryable=True
                    )
                if status != 200:
                    raise RequestError("http", f"HTTP {status}，请求失败。")
                content = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    self.response_bytes += len(chunk)
                    if len(content) + len(chunk) > self.settings.max_response_bytes:
                        raise RequestError("response_size", "API 响应超过配置的字节预算。")
                    content.extend(chunk)
                self.timings["http_seconds"] += self.clock() - http_started
                self.on_phase("解析响应")
                parse_started = self.clock()
                try:
                    body = json.loads(content, parse_float=Decimal, parse_constant=_reject_constant)
                except (ValueError, UnicodeError):
                    raise RequestError("protocol", "API 响应不是有效 JSON。") from None
                if not isinstance(body, dict) or type(body.get("code")) is not int:
                    raise RequestError("protocol", "API 响应缺少有效业务码。")
                if body["code"] != 0:
                    # Do not relay arbitrary server messages that may echo credentials.
                    raise RequestError("business", f"API 业务错误（code={body['code']}）。")
                rows, received, duplicates = parse_rows(body.get("data"), api)
                return ApiResult(rows, received, duplicates, attempt)
            except requests.exceptions.SSLError:
                raise RequestError("tls", "TLS 证书验证失败。") from None
            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.exceptions.ChunkedEncodingError,
            ):
                error = RequestError("network", "连接或读取失败。", retryable=True)
            except requests.RequestException:
                raise RequestError("transport", "HTTP 传输失败。") from None
            except RequestError as exc:
                if not exc.retryable:
                    raise
                error = exc
            finally:
                if parse_started is not None:
                    self.timings["parse_seconds"] += self.clock() - parse_started
                else:
                    self.timings["http_seconds"] += self.clock() - http_started
                if response is not None:
                    response.close()
            if attempt == self.settings.max_attempts:
                raise RequestError(
                    error.category, f"{error} 已达到 {attempt} 次尝试上限。"
                ) from None
            delay = max(
                wait,
                min(self.settings.retry_max_seconds, 2 ** min(attempt - 1, 20) + self.jitter()),
            )
            if self.on_retry:
                self.on_retry(error.category, attempt, delay)
            self.on_phase("重试等待")
            before_wait = self.clock()
            self.sleep(delay)
            self.timings["retry_seconds"] += self.clock() - before_wait
        raise AssertionError("unreachable")
