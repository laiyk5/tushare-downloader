# 快速开始

运行环境为 WSL/Linux Python 3.12，数据库可运行在 Windows。
准备 uv、PostgreSQL 服务，以及具备对应接口权限的 Tushare Pro Token。
数据库管理员先按[数据库初始化](../operations/database.md)创建库和账号。

```bash
git clone git@github.com:laiyk5/tushare-downloader.git
cd tushare-downloader
uv sync --locked
# 仅在首次创建配置时复制，不覆盖已有 .env
if [ ! -e .env ]; then cp .env.example .env; fi
chmod 600 .env
```

编辑 `.env` 中的 `TUSHARE_TOKEN`、`PGHOST`、`PGPORT`、`PGDATABASE`、`PGUSER`、`PGPASSWORD`。
默认库名为 `tushare`，账号为 `tushare_writer`；凭据不要提交 Git。
已有库不要重复创建，已有配置不要直接覆盖。全部配置见[配置参考](configuration.md)。

```bash
uv run tushare-downloader list
uv run tushare-downloader init-db
uv run tushare-downloader f daily_basic -s 2024-01-02 -e 2024-01-05 --dry-run
uv run tushare-downloader f daily_basic -s 2024-01-02 -e 2024-01-05
```

`list` 不访问数据库或 Tushare；`init-db` 建立并校验受管理表。
`--dry-run` 读取本地数据库并输出计划，不请求 Tushare、不修改数据库。
正式下载会消耗 API 额度；空响应会作为待核实结果报告。

终端给出完整报告和 JSONL 日志路径。再次运行同范围 `fetch` 会按有效检查记录跳过，
失败部分可重新运行补齐。后续更新和历史修正见[下载与报告](downloading.md)。
