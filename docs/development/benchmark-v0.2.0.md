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

## Full executor and layered runs

2026-09-14; dedicated Windows PostgreSQL 18 on port 55432, database and non-superuser role `tushare_bench`. Production was not used. Flow uses 100 rows per date, CPU/database use 1,000. Every scenario repeats five times. These fixtures disable real HTTP waits; results do not predict actual API download speed. Flow explicitly uses calendar off to preserve fixed request cases.

### flow

| Scenario | Runs | Median seconds | MAD |
| --- | ---: | ---: | ---: |
| initial | 5 | 0.079657 | 0.002201 |
| skip_all | 5 | 0.012274 | 0.000058 |
| middle_failed | 5 | 0.027065 | 0.000443 |
| partial_expired | 5 | 0.042162 | 0.000552 |
| refresh_all | 5 | 0.082256 | 0.000996 |
| append_update | 5 | 0.078897 | 0.000853 |
| mutable_delete | 5 | 0.020378 | 0.000689 |
| mutable_reappear | 5 | 0.022420 | 0.000468 |
| empty | 5 | 0.051210 | 0.000277 |
| duplicates | 5 | 0.078397 | 0.000691 |
| partial_failure | 5 | 0.066368 | 0.000205 |
| long_report | 5 | 1.113422 | 0.016202 |

[Samples](benchmark-v0.2.0-flow/samples.jsonl), [summary](benchmark-v0.2.0-flow/summary.json), [environment](benchmark-v0.2.0-flow/environment.json).

### cpu

| Scenario | Runs | Median seconds | MAD |
| --- | ---: | ---: | ---: |
| http_parse | 5 | 0.027552 | 0.000401 |
| http_parse_duplicates | 5 | 0.029636 | 0.000064 |
| plan_initial | 5 | 0.014448 | 0.000038 |
| plan_skip_all | 5 | 0.016956 | 0.000100 |
| plan_middle_failed | 5 | 0.021164 | 0.000312 |
| plan_partial_expired | 5 | 0.022616 | 0.000087 |
| plan_refresh_all | 5 | 0.024160 | 0.000120 |
| plan_update_window | 5 | 0.014391 | 0.000021 |
| plan_empty | 5 | 0.020395 | 0.000204 |
| block_1d | 5 | 0.000318 | 0.000003 |
| block_7d | 5 | 0.000308 | 0.000003 |
| block_30d | 5 | 0.000312 | 0.000007 |
| report_plain | 5 | 0.013384 | 0.000080 |
| report_off | 5 | 0.012994 | 0.000149 |
| report_debug | 5 | 0.013914 | 0.000117 |
| report_rich | 5 | 0.028709 | 0.000348 |

[Samples](benchmark-v0.2.0-cpu/samples.jsonl), [summary](benchmark-v0.2.0-cpu/summary.json), [environment](benchmark-v0.2.0-cpu/environment.json).

### database

| Scenario | Runs | Median seconds | MAD |
| --- | ---: | ---: | ---: |
| db_insert | 5 | 0.026817 | 0.000511 |
| db_unchanged | 5 | 0.029259 | 0.000315 |
| db_changed | 5 | 0.019699 | 0.000397 |
| db_stale | 5 | 0.037483 | 0.000417 |
| db_reactivate | 5 | 0.030327 | 0.000605 |
| db_empty | 5 | 0.007552 | 0.000100 |

[Samples](benchmark-v0.2.0-database/samples.jsonl), [summary](benchmark-v0.2.0-database/summary.json), [environment](benchmark-v0.2.0-database/environment.json).
