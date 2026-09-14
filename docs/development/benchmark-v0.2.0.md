# Calendar planning benchmark

2026-09-14. Run with `uv run python benchmarks/calendar_compare.py`.
This is a deterministic planner/cache benchmark with a fake calendar provider; it does not measure network or database throughput. Each of six scenarios runs five times. Fixture: 366 dates in 2024, weekends and January 1 closed; this is not a real exchange calendar.

Off and bypass select 366 dates; basic selects 262; cold/hot calendar select 261. Hot-cache setup is outside measurement. The failure case demonstrates stopping, not speedup.

| Scenario | Runs | Median seconds | Min | Max | MAD |
| --- | ---: | ---: | ---: | ---: | ---: |
| off | 5 | 0.000219 | 0.000208 | 0.000252 | 0.000012 |
| basic | 5 | 0.000192 | 0.000180 | 0.000314 | 0.000012 |
| calendar_cold | 5 | 0.004350 | 0.004248 | 0.004708 | 0.000066 |
| calendar_hot | 5 | 0.001285 | 0.001266 | 0.001360 | 0.000019 |
| bypass | 5 | 0.000194 | 0.000190 | 0.000221 | 0.000003 |
| calendar_failure | 5 | 0.000255 | 0.000213 | 0.000298 | 0.000005 |

[Raw samples](benchmark-v0.2.0-calendar/samples.jsonl), [summary](benchmark-v0.2.0-calendar/summary.json), [environment](benchmark-v0.2.0-calendar/environment.json). Full executor/database and output-mode comparisons remain separate acceptance work.
