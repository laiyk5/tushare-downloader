"""Compare calendar planning cost with deterministic responses, not real network speed."""

import argparse
import json
import platform
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from run import measured, summarize

from tushare_downloader.apis import get_api
from tushare_downloader.calendar import CalendarError, filter_requests
from tushare_downloader.client import RequestError
from tushare_downloader.config import Settings
from tushare_downloader.planning import blocks


def run(output, repeat=5):
    if repeat < 5:
        raise ValueError("At least five repetitions are required.")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    start, end = date(2024, 1, 1), date(2024, 12, 31)
    pending = [
        (b, "unseen")
        for b in blocks(
            start, end, origin=date(1970, 1, 1), size=1, available_start=start, available_end=end
        )
    ]
    api = get_api("daily_basic")
    samples = []
    for case in ("off", "basic", "calendar_cold", "calendar_hot", "bypass", "calendar_failure"):
        for iteration in range(1, repeat + 1):
            with TemporaryDirectory() as folder:
                settings = Settings(
                    calendar_filter="calendar" if case not in {"off", "basic"} else case,
                    calendar_cache_dir=Path(folder),
                )

                class Client:
                    attempts = 0

                    def __init__(self, *args, **kwargs):
                        pass

                    def close(self):
                        pass

                    def query(self, spec, params):
                        self.attempts += 1
                        if case == "calendar_failure":
                            raise RequestError("network", "simulated outage")
                        # Fixed fixture: weekends plus Jan 1 closed. Not a market calendar claim.
                        return SimpleNamespace(
                            rows=[
                                (
                                    "SSE",
                                    start + timedelta(days=i),
                                    "1" if (start + timedelta(days=i)).weekday() < 5 and i else "0",
                                )
                                for i in range(366)
                            ]
                        )

                if case == "calendar_hot":
                    filter_requests(api, pending, settings, now=now, client_factory=Client)

                def operation():
                    try:
                        result = filter_requests(
                            api,
                            pending,
                            settings,
                            now=now,
                            client_factory=Client,
                            ignore=case == "bypass",
                        )
                    except CalendarError:
                        if case != "calendar_failure":
                            raise
                        return {"preparation_failed": True, "data_requests": 0}
                    selected = [str(b.requested_start) for b, _ in result.requested]
                    if case in {"off", "bypass"}:
                        assert len(selected) == 366
                    elif case == "basic":
                        assert len(selected) == 262
                    else:
                        assert len(selected) == 261
                    return {
                        "preparation_failed": False,
                        "planned_data_requests": len(selected),
                        "calendar_requests": result.attempts,
                        "filtered": len(result.filtered),
                        "selected_dates": selected,
                    }

                samples.append({**measured(operation), "scenario": case, "iteration": iteration})
    output.mkdir(parents=True, exist_ok=True)
    (output / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))
    (output / "summary.json").write_text(json.dumps(summarize(samples), indent=2))
    (output / "environment.json").write_text(
        json.dumps(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "fixture": "366 dates, weekends and Jan 1 closed",
                "scope": "calendar planner including cache read/write; fake API, no database",
                "warmup": "hot cache seeded outside measurement",
                "failure": "not an acceleration result",
            },
            indent=2,
        )
    )
    print(output / "summary.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/calendar"))
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()
    run(args.output, args.repeat)
