# 开发环境与配置

项目位于 WSL：/home/laiyk/projects/tools/tushare-downloader。
Python 与依赖版本由 .python-version、uv.lock 固定。

```bash
uv sync --locked --all-groups
uv run pre-commit install
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=tushare_downloader --cov-branch
uv build
uv run zensical build --strict
```

默认 pytest 只跑无需外部服务的单元测试。真实 PostgreSQL 集成测试需专用库和账号：

```bash
TEST_DATABASE_URL='postgresql://tushare_test:测试密码@localhost:55432/tushare_test' \
  uv run pytest tests/integration
```

集成测试会删除该测试库的 raw/meta 对象；缺失配置或数据库/账号名称不匹配会报错。
CI 的 PostgreSQL 服务为临时测试实例，不能使用正式库连接。

## 配置

当前目录 .env（或 -c 指定文件）→ 环境变量覆盖；--plain 可进一步启用纯文本。
不搜索父目录、不插值展开 .env 变量。相对路径以当前工作目录为基准。
.env.example 包含默认项。已有 .env 请直接编辑，不要覆盖。

正式库 tushare、账号 tushare_writer；本机已验证 WSL 可通过 localhost:5432 连接 Windows PostgreSQL。
Token、密码不进入 Git、终端参数或报告。list 不需要凭据，init-db/clean 不需要 Tushare Token。

HTTP 配置：REQUESTS_PER_MINUTE、MAX_ATTEMPTS、CONNECT_TIMEOUT_SECONDS、READ_TIMEOUT_SECONDS、
RETRY_MAX_SECONDS、MAX_RESPONSE_BYTES。MAX_ATTEMPTS 包括首次请求；默认响应预算 32 MiB。
LOG_DIR/REPORT_DIR 控制输出路径；PROGRESS=off 关闭周期进度；PLAIN=true 关闭动态显示。
LOG_LEVEL 控制可选诊断，关键结果不会因日志级别而丢失。

## 常用命令

```bash
uv run tushare-downloader list
uv run tushare-downloader init-db
uv run tushare-downloader --plain f daily_basic -s 2024-01-02 -e 2024-01-05 --dry-run
uv run tushare-downloader f daily_basic -s 2024-01-02 -e 2024-01-05
uv run tushare-downloader refresh daily_basic -s 2024-01-02 -e 2024-01-05 --max-age 0
uv run tushare-downloader u stock_basic
uv run tushare-downloader clean daily_basic
```

clean 默认只预览。实际清理必须加 --apply，并提供匹配的 --confirm-database 和
--confirm-database-id；它不会级联删除下游外键引用。当前不需要清理正式样本数据。

fetch/refresh 时间区间包含端点；update 的回看从本地最新 active 日期开始计算。
快照不能指定日期。下载前后报告分别保存在 reports/每次调用目录下，
结构化日志保存在 logs/*.jsonl；轮转片段保留全部事件。查看示例：

```bash
# 从终端结束摘要取得本次具体日志路径后设置：
LOG_FILE='./logs/替换为实际文件名.jsonl'
jq -c 'select(.event == "slice_result")' "$LOG_FILE"
```

## 实现范围

cli.py 负责命令，config.py 读取配置，apis/ 声明接口，
planning.py 计算请求块，client.py 处理 HTTPS/重试/解析，
storage.py 处理身份校验与原子 SQL，download.py 串联执行，
reporting.py 输出进度、报告和日志。没有任务管理层。

测试采用等价类与边界，不声称少量例子可证明全部输入正确。
真实接口与尚待完善内容见[验证记录](verification.md)。
