# Benchmark

All samples are retained; durations are seconds. Python memory sampling is enabled and adds overhead.

| Scenario | Samples | Median | Minimum | Maximum | MAD |
|---|---:|---:|---:|---:|---:|
| http_parse | 5 | 0.003586 | 0.002894 | 0.004063 | 0.000477 |
| http_parse_duplicates | 5 | 0.003272 | 0.003188 | 0.003879 | 0.000085 |
| plan_initial | 5 | 0.001486 | 0.001439 | 0.001634 | 0.000041 |
| plan_skip_all | 5 | 0.001817 | 0.001729 | 0.001940 | 0.000075 |
| plan_middle_failed | 5 | 0.002145 | 0.002082 | 0.002480 | 0.000055 |
| plan_partial_expired | 5 | 0.002475 | 0.002273 | 0.002939 | 0.000109 |
| plan_refresh_all | 5 | 0.002545 | 0.002432 | 0.003235 | 0.000113 |
| plan_update_window | 5 | 0.001463 | 0.001453 | 0.001495 | 0.000010 |
| plan_empty | 5 | 0.002161 | 0.002077 | 0.002246 | 0.000034 |
| block_1d | 5 | 0.000333 | 0.000324 | 0.000347 | 0.000002 |
| block_7d | 5 | 0.000312 | 0.000311 | 0.000341 | 0.000001 |
| block_30d | 5 | 0.000319 | 0.000312 | 0.000355 | 0.000008 |
| report_plain | 5 | 0.004548 | 0.003595 | 0.005947 | 0.000499 |
| report_off | 5 | 0.003697 | 0.003279 | 0.004103 | 0.000145 |
| report_debug | 5 | 0.004374 | 0.004111 | 0.004923 | 0.000263 |
| report_rich | 5 | 0.011606 | 0.010668 | 0.024844 | 0.000504 |
