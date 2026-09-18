# v0.3.0 端到端基准记录

2026-09-15，WSL Python + Windows PostgreSQL 18 临时专用 tushare_bench 库。五个日频接口使用同一执行器与固定 HTTP 响应，每日 100 行，每场景重复 5 次。包含 12 个场景，每接口 60 次，共 300 次执行；mutable 场景仍使用 stock_basic，不能将它们算作日频接口能力。

命令：`uv run python benchmarks/flow.py --api API --rows 100 --repeat 5`，通过 BENCH_DATABASE_URL 指定专用库。
网络与等待关闭、日历显式 off、progress off；普通报告和 INFO 文件日志开启。准备数据与读取摘要不计入耗时，tracemalloc 开启。
以下为中位数；完整样本、最初产物路径及环境见 [JSON 证据](benchmark-v0.3.0.json)。字段宽度不同，不能仅凭耗时差异判断框架退化；此表比较本版不同接口，不是旧版本速度对照。

| API | 场景 | 次数 | 墙钟秒 | 数据请求 | 已提交输入行 | Python 峰值 KiB |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| daily_basic | initial | 5 | 0.085693 | 5 | 500 | 544.9 |
| daily_basic | skip_all | 5 | 0.012653 | 0 | 0 | 67.5 |
| daily_basic | refresh_all | 5 | 0.089213 | 5 | 500 | 459.9 |
| daily_basic | append_update | 5 | 0.084882 | 5 | 500 | 459.7 |
| daily_basic | empty | 5 | 0.055974 | 5 | 0 | 79.7 |
| daily_basic | partial_failure | 5 | 0.072428 | 8 | 400 | 461.7 |
| daily_basic | long_report | 5 | 1.177667 | 100 | 5000 | 396.1 |
| daily | initial | 5 | 0.075244 | 5 | 500 | 363.1 |
| daily | skip_all | 5 | 0.013782 | 0 | 0 | 67.7 |
| daily | refresh_all | 5 | 0.084514 | 5 | 500 | 297.1 |
| daily | append_update | 5 | 0.077983 | 5 | 500 | 298.1 |
| daily | empty | 5 | 0.052929 | 5 | 0 | 77.0 |
| daily | partial_failure | 5 | 0.065250 | 8 | 400 | 299.2 |
| daily | long_report | 5 | 1.145295 | 100 | 5000 | 310.1 |
| adj_factor | initial | 5 | 0.066646 | 5 | 500 | 158.6 |
| adj_factor | skip_all | 5 | 0.013687 | 0 | 0 | 67.7 |
| adj_factor | refresh_all | 5 | 0.073706 | 5 | 500 | 108.8 |
| adj_factor | append_update | 5 | 0.069155 | 5 | 500 | 109.0 |
| adj_factor | empty | 5 | 0.053250 | 5 | 0 | 74.0 |
| adj_factor | partial_failure | 5 | 0.060418 | 8 | 400 | 110.3 |
| adj_factor | long_report | 5 | 1.061077 | 100 | 5000 | 220.7 |
| stk_limit | initial | 5 | 0.069564 | 5 | 500 | 206.2 |
| stk_limit | skip_all | 5 | 0.013050 | 0 | 0 | 68.2 |
| stk_limit | refresh_all | 5 | 0.076013 | 5 | 500 | 157.0 |
| stk_limit | append_update | 5 | 0.070252 | 5 | 500 | 157.0 |
| stk_limit | empty | 5 | 0.050955 | 5 | 0 | 74.6 |
| stk_limit | partial_failure | 5 | 0.059679 | 8 | 400 | 157.8 |
| stk_limit | long_report | 5 | 1.037260 | 100 | 5000 | 223.2 |
| suspend_d | initial | 5 | 0.066276 | 5 | 500 | 156.7 |
| suspend_d | skip_all | 5 | 0.013185 | 0 | 0 | 67.9 |
| suspend_d | refresh_all | 5 | 0.072108 | 5 | 500 | 94.4 |
| suspend_d | append_update | 5 | 0.067305 | 5 | 500 | 93.8 |
| suspend_d | empty | 5 | 0.050920 | 5 | 0 | 74.7 |
| suspend_d | partial_failure | 5 | 0.057420 | 8 | 400 | 96.1 |
| suspend_d | long_report | 5 | 1.006806 | 100 | 5000 | 217.2 |

所有场景退出码均符合脚本预期：partial_failure 为 1，其余为 0；失败场景仍保留已提交日期。
skip_all 不发数据请求；结果不证明真实 API 延迟、服务器内存或所有市场日期的完整性。固定响应基准与真实 API 冒烟分别记录。
