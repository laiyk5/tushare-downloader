from tushare_downloader.apis import ApiSpec, Field
from tushare_downloader.client import TushareClient
from tushare_downloader.config import Settings


def test_phase_metrics_count_http_and_wait_separately():
    class Clock:
        now = 0.0

        def __call__(self):
            return self.now

        def sleep(self, value):
            self.now += value

    clock = Clock()

    class Response:
        status_code = 200
        headers = {}

        def iter_content(self, chunk_size):
            clock.now += 0.75
            yield b'{"code":0,"data":{"fields":["key"],"items":[["001"]]}}'

        def close(self):
            pass

    class Session:
        def post(self, *args, **kwargs):
            clock.now += 0.25
            return Response()

    api = ApiSpec(
        "test", (Field("key", "text", False),), ("key",), "append-only", "snapshot", frozenset()
    )
    phases = []
    client = TushareClient(
        Settings(token="fixture"),
        session=Session(),
        clock=clock,
        sleep=clock.sleep,
        on_phase=phases.append,
    )
    result = client.query(api, {})
    assert result.rows == (("001",),)
    assert phases == ["Rate-limit waiting", "HTTP request", "Parsing response"]
    assert client.timings == {
        "http_seconds": 1,
        "parse_seconds": 0,
        "pacing_seconds": 1,
        "retry_seconds": 0,
    }
    assert client.attempts == 1 and client.response_bytes > 0
