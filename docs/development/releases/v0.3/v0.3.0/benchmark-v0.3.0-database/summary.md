# Benchmark

All samples are retained; durations are seconds. Python memory sampling is enabled and adds overhead.

| Scenario | Samples | Median | Minimum | Maximum | MAD |
|---|---:|---:|---:|---:|---:|
| db_insert | 5 | 0.011078 | 0.010582 | 0.013447 | 0.000231 |
| db_unchanged | 5 | 0.010913 | 0.010585 | 0.011992 | 0.000329 |
| db_changed | 5 | 0.009554 | 0.009308 | 0.009843 | 0.000075 |
| db_stale | 5 | 0.010421 | 0.010149 | 0.010582 | 0.000081 |
| db_reactivate | 5 | 0.011279 | 0.010642 | 0.011394 | 0.000114 |
| db_empty | 5 | 0.007924 | 0.007717 | 0.008350 | 0.000181 |
