# 配置模板与忽略规则

**设计版本：v0.2.0-draft.6**。以下为拟采用模板，不修改当前实际 .env、.env.example 或 .gitignore。

## 原则

继续采用单个 dotenv 文件，通过英文分组注释和稳定顺序提升可读性，不引入 TOML/YAML、配置框架或更多必需文件。
凭据、运行策略、展示偏好和开发专用连接分开；空值仅用于明确需要用户填写的字段，不用空值代替可选项默认值。
现有默认值及配置优先级保持不变。新增交易日过滤和终端日志字段按本版对应设计实现，不能宣称 v0.1.0 已支持。
注释说明用途、单位、必要限制；复杂行为链接参考文档，不把设计论文塞进模板。

## .env.example 模板

```dotenv
# Local configuration. Never commit real credentials.
# Environment variables override this file. Relative paths use the working directory.

# --- Credentials ---
# Required for remote data requests.
TUSHARE_TOKEN=

# --- Database ---
PGHOST=localhost
# TCP port: 1..65535.
PGPORT=5432
PGDATABASE=tushare
PGUSER=tushare_writer
# Supply a password if required by your PostgreSQL authentication setup.
PGPASSWORD=
# disable / allow / prefer / require / verify-ca / verify-full
PGSSLMODE=prefer

# --- Requests & retries ---
# Positive request budget per minute; API-specific limits still apply.
REQUESTS_PER_MINUTE=60
# Total attempts, including the initial request; integer >= 1.
MAX_ATTEMPTS=4
# Seconds; each must be an integer >= 1.
CONNECT_TIMEOUT_SECONDS=10
READ_TIMEOUT_SECONDS=60
RETRY_MAX_SECONDS=60
# Bytes; 33554432 = 32 MiB. Must be positive.
MAX_RESPONSE_BYTES=33554432
# Stop after this many consecutive failed blocks; 0 disables this threshold.
MAX_CONSECUTIVE_FAILED_SLICES=10

# --- Refresh & update ---
# Freshness threshold, e.g. 12h or 7d. Use 0 to force refresh.
MAX_AGE=24h
# Calendar days counted backward from the latest local date, inclusive; integer >= 1.
LOOKBACK_DAYS=7
# Positive duration before rechecking a successful empty response.
EMPTY_RECHECK_AGE=24h

# --- Trading-day filter (v0.2.0) ---
# basic: weekends; calendar: external trading calendar; off: no filtering.
# Calendar preparation failure does not automatically change this choice.
CALENDAR_FILTER=basic
# Used only by calendar mode. Cache contents are disposable.
CALENDAR_CACHE_DIR=./.cache/tushare-downloader/calendar
# Positive duration; used only by calendar mode.
CALENDAR_MAX_AGE=24h

# --- Logs & reports ---
LOG_DIR=./logs
REPORT_DIR=./reports
# File logging: DEBUG / INFO / WARNING / ERROR. Independent of -q/-v.
LOG_LEVEL=INFO

# --- Terminal output ---
# true/false (also accepts 1/0). Unsupported terminals use plain output automatically.
PLAIN=false
# auto / off; off suppresses progress, not warnings or errors.
PROGRESS=auto
# Seconds between static progress updates: 1..60.
PROGRESS_INTERVAL_SECONDS=5
# Rich recent activity entries: 0..20; 0 hides the activity list (v0.2.0).
TERMINAL_LOG_LINES=5
# Maximum summary items per category; integer >= 1. Full reports are not truncated.
REPORT_MAX_ITEMS=20

# --- Development only ---
# Tests and benchmarks read these from the PROCESS ENVIRONMENT, not this dotenv file.
# They never fall back to the production database settings above.
# These commented names are reminders, not active downloader configuration.
# TEST_DATABASE_URL=
# BENCH_DATABASE_URL=
```

最后一组仅列出名称和边界。测试入口当前读取 os.environ；在 .env 中填写 TEST_DATABASE_URL 不会自动让 pytest 读取它。
贡献者指南给出环境注入方法；不新增自动加载正式 .env 的测试逻辑，不建议通过 source 执行 dotenv 文件。
密码和 Token 不在文档、日志、错误或整理过程输出中出现。示例连接如有需要只能使用占位值。

## .gitignore 模板

现有条目只移动，不改变是否匹配子目录等语义；仅新增精确的默认日历缓存目录。

```gitignore
# --- Credentials & local configuration ---
.env
.env.*
!.env.example

# --- Python & environments ---
__pycache__/
*.py[cod]
.venv/

# --- Build artifacts ---
build/
dist/
wheels/
*.egg-info/

# --- Tests & coverage ---
.pytest_cache/
.coverage
.coverage.*
coverage.xml
htmlcov/

# --- Tool caches ---
.ruff_cache/

# --- Runtime output ---
logs/
reports/
.cache/tushare-downloader/calendar/

# --- Documentation ---
site/

# --- Benchmarks ---
benchmarks/results/
```

不忽略 uv.lock、设计文档、静态 demo、文档中的报告样例，也不使用 *.log、*.json、*.html 等过宽规则。
自定义日志/报告/缓存路径落在仓库内时，由用户补充对应忽略规则；gitignore 不会自动读取配置值。
忽略规则不移除已经跟踪的文件；实现时只核对当前状态，不擅自批量取消 Git 跟踪。

## 实施与旧配置保留

1. 根据代码和本版设计核对模板键名、默认值、单位及取值范围。
2. 整理 .env.example 与 .gitignore；本地 .env 整理保留所有现值、未知自定义键及必要注释，不从示例覆盖文件。
3. 新增项缺失时由代码默认值生效；如补入本地文件，只补缺失项。已有重复键不得随意合并，避免改变当前解析结果。
4. 原有 TEST_DATABASE_URL 即使出现在本地 .env，也不擅自删除；说明它对当前测试入口不生效，避免悄悄改变加载语义。
5. 文档参考页和模板同步；真实本地文件不提交，实际值不打印用于比对。

开发者手动整理即可，不新增配置迁移命令或自动重写用户配置机制。
CLI --plain、环境变量、指定 dotenv 与默认值之间的既有优先级不变；NO_COLOR 和终端能力降级按 CLI 设计。

## 文档目录落点

沿用现有目录：guide（操作）、reference（完整参数）、operations（数据库维护）、development（开发流程）、design（中文设计）。
README 主导航按快速开始、配置、下载指南、CLI 参考、在线文档组织；贡献者入口再链接设计、开发、验收与部署。
配置默认值和取值范围由 reference/guide 对应配置页集中解释，README 只给最小上手步骤；内部待办仍放 backlog。
本页是设计规范，不取代发布后的英文用户配置参考。

## 验收

- 对照配置加载器检查示例键、默认值和单位，新增项仅在实现后加入实际模板。
- 整理前后相同配置得到相同有效值；新默认项和注释之外没有非预期变化，不在测试输出暴露凭据。
- 用代表路径验证 gitignore：.env/.env.local 被忽略，.env.example、uv.lock、设计/demo 保留；原产物规则不变。
- 默认日历缓存被忽略，自定义路径边界有说明；不扩大为忽略整个 .cache 或任意 JSON。
- 测试和 benchmark 仍只接受独立的环境连接配置；不回落正式库。
