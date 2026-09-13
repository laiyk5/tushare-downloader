import json
from datetime import date
from decimal import Decimal

import pytest
import requests

from tushare_downloader.apis import ApiSpec, Field
from tushare_downloader.client import RequestError, TushareClient, parse_rows
from tushare_downloader.config import Settings

API = ApiSpec(
    "example",
    (Field("key", "text", False), Field("day", "date"), Field("value", "decimal")),
    ("key",),
    "append-only",
    "time-range",
    frozenset(),
    row_limit=1,
)


def data(items=None):
    return {
        "fields": ["value", "key", "day"],
        "items": items if items is not None else [["1.25", "001", "20240102"]],
    }


class Response:
    def __init__(self, status=200, body=None, headers=None, raw=None):
        self.status_code = status
        self.headers = headers or {}
        self.raw = (
            raw
            if raw is not None
            else json.dumps(body if body is not None else {"code": 0, "data": data()}).encode()
        )
        self.closed = False

    def iter_content(self, **kwargs):
        yield self.raw

    def close(self):
        self.closed = True


class Session:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        item = next(self.outcomes)
        if isinstance(item, Exception):
            raise item
        return item


class Clock:
    def __init__(self):
        self.now = 0
        self.waits = []

    def time(self):
        return self.now

    def sleep(self, delay):
        self.waits.append(delay)
        self.now += delay


def client(outcomes, **settings):
    session, clock = Session(outcomes), Clock()
    result = TushareClient(
        Settings(token="secret-token", **settings),
        session=session,
        clock=clock.time,
        sleep=clock.sleep,
        jitter=lambda: 0,
    )
    return result, session, clock


def test_parser_reorders_and_preserves_types():
    rows, count, duplicates = parse_rows(data(), API)
    assert rows == (("001", date(2024, 1, 2), Decimal("1.25")),)
    assert (count, duplicates) == (1, 0)


def test_identical_duplicates_and_conflicts():
    item = ["1.25", "001", ""]
    assert parse_rows(data([item, item]), API)[1:] == (2, 1)
    with pytest.raises(RequestError, match="同键"):
        parse_rows(data([item, ["2", "001", ""]]), API)


@pytest.mark.parametrize(
    "item",
    [
        [True, "001", ""],
        ["NaN", "001", ""],
        ["1", None, ""],
        ["1", "001", "20240230"],
        ["1", 1, ""],
        ["1"],
    ],
)
def test_malformed_rows(item):
    with pytest.raises(RequestError):
        parse_rows(data([item]), API)


def test_at_row_limit_is_success():
    transport, session, _ = client([Response()])
    assert transport.query(API, {}).received_rows == API.row_limit
    assert session.calls[0][0].startswith("https:")
    assert session.calls[0][1]["allow_redirects"] is False


def test_business_error_is_failure_without_secret_echo():
    transport, session, _ = client([Response(body={"code": -2001, "msg": "secret-token"})])
    with pytest.raises(RequestError) as error:
        transport.query(API, {})
    assert error.value.category == "business"
    assert "secret-token" not in str(error.value)
    assert len(session.calls) == 1


def test_retry_after_and_pacing():
    first = Response(429, headers={"Retry-After": "3"})
    second = Response()
    transport, session, clock = client([first, second])
    assert transport.query(API, {}).attempts == 2
    assert clock.waits == [1, 3]
    assert first.closed and second.closed
    assert len(session.calls) == 2


def test_retry_exhaustion():
    transport, session, _ = client([requests.Timeout("secret-token") for _ in range(4)])
    with pytest.raises(RequestError) as error:
        transport.query(API, {})
    assert error.value.category == "network"
    assert "secret-token" not in str(error.value)
    assert len(session.calls) == 4


@pytest.mark.parametrize(
    "outcome,category",
    [
        (requests.exceptions.SSLError("secret-token"), "tls"),
        (Response(401), "http"),
        (Response(429, headers={"Retry-After": "600"}), "retry_deferred"),
        (Response(raw=b'{"code":0,"data":NaN}'), "protocol"),
        (Response(body={"code": True}), "protocol"),
    ],
)
def test_nonretryable_errors(outcome, category):
    transport, session, _ = client([outcome])
    with pytest.raises(RequestError) as error:
        transport.query(API, {})
    assert error.value.category == category
    assert len(session.calls) == 1


def test_response_budget_and_parameter_whitelist():
    transport, session, _ = client([Response()], max_response_bytes=1)
    with pytest.raises(RequestError) as error:
        transport.query(API, {})
    assert error.value.category == "response_size"
    with pytest.raises(RequestError):
        transport.query(API, {"unknown": "value"})
    assert len(session.calls) == 1
