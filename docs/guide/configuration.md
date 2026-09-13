# 配置

下载器读取当前工作目录的 `.env`；`-c FILE` 可指定另一文件。环境变量覆盖文件，
未配置项使用默认值。不会搜索父目录，也不展开 `.env` 中的变量引用。
相对日志和报告路径相对于工作目录，不相对于配置文件目录。

```bash
uv run tushare-downloader -c ./config/local.env --plain list
```

`--plain` 可进一步启用纯文本；`NO_COLOR` 环境变量存在时也启用纯文本。
常用展示偏好写入配置，不必每次放到命令里。配置项区分大小写。

## 连接与凭据

| 配置项 | 默认值 | 用途 |
| --- | --- | --- |
| TUSHARE_TOKEN | 空 | 真正发起 API 请求时必需 |
| PGHOST / PGPORT | localhost / 5432 | PostgreSQL 地址和端口 |
| PGDATABASE / PGUSER | tushare / tushare_writer | 正式库和下载账号 |
| PGPASSWORD | 空 | 数据库密码 |
| PGSSLMODE | prefer | libpq SSL 模式；远程连接应使用 verify-full 并配置可信证书 |

凭据只保存在本机受限文件或环境变量中，不放命令参数、文档或日志。
`init-db`、`clean`、`--dry-run` 不需要 Token，但需要数据库。

## 下载策略

| 配置项 | 默认值 | 含义 |
| --- | --- | --- |
| MAX_AGE | 24h | refresh 的最大核对年龄；命令 --max-age 可覆盖；0 强制 |
| LOOKBACK_DAYS | 7 | 只增型 update 的回看天数，包含本地最新 active 日期 |
| EMPTY_RECHECK_AGE | 24h | 成功空响应的重查年龄，必须大于零 |
| REQUESTS_PER_MINUTE | 60 | 请求频率预算，按账户权限配置 |
| MAX_ATTEMPTS | 4 | 单次请求最多尝试次数，包含首次 |
| MAX_CONSECUTIVE_FAILED_SLICES | 10 | 连续失败段停止阈值；0 关闭此阈值 |
| CONNECT_TIMEOUT_SECONDS | 10 | 连接超时 |
| READ_TIMEOUT_SECONDS | 60 | 读取超时 |
| RETRY_MAX_SECONDS | 60 | 重试等待上限 |
| MAX_RESPONSE_BYTES | 33554432 | 单次响应体预算，默认 32 MiB |

时长接受 `30s`、`5m`、`24h`、`7d`；允许强制的项也接受 `0`。
除单独注明可为零的项外，整数预算必须为正数。

## 输出偏好

| 配置项 | 默认值 | 含义 |
| --- | --- | --- |
| LOG_DIR / REPORT_DIR | ./logs / ./reports | JSONL 和完整 Markdown 报告目录 |
| LOG_LEVEL | INFO | DEBUG / INFO / WARNING / ERROR；关键结果始终保留 |
| PROGRESS | auto | auto 或 off |
| PLAIN | false | true/false 或 1/0；关闭动态显示与 ANSI |
| PROGRESS_INTERVAL_SECONDS | 5 | 周期展示间隔，1–60 秒 |
| REPORT_MAX_ITEMS | 20 | 每个分类在终端显示的明细上限，文件保留全量 |

`-q` 减少常规输出，`-v` 显示分段详情；两者不能同时使用。
日志阅读方式见[下载与报告](downloading.md)。

## 测试和 benchmark 的独立连接

`TEST_DATABASE_URL` 只供集成测试使用，`BENCH_DATABASE_URL` 只供数据库 benchmark 使用。
两者通过进程环境变量提供，不由下载器自动读取 `.env` 后传给测试。
日常下载不必填写。必须指向专用库，配置缺失时不会回落正式库。
详见[测试](../development/testing.md)和[Benchmark](../development/benchmarks.md)。
