# tushare-downloader

Tushare Pro → PostgreSQL 下载工具。当前支持 daily_basic 和 stock_basic 的基础下载、核对与更新。

- [设计入口](docs/design/index.md)
- [快速开始](docs/guide/quickstart.md)
- [配置](docs/guide/configuration.md)
- [开发环境](docs/development/setup.md)
- [验收记录](docs/development/acceptance.md)
- [在线文档](https://laiyk5.github.io/tushare-downloader/)
- [文档部署](docs/development/documentation.md)

## 开始使用（Bash / WSL）

```bash
uv sync --locked --all-groups
uv run tushare-downloader list
uv run tushare-downloader init-db
uv run tushare-downloader f daily_basic -s 2024-01-02 -e 2024-01-02
uv run tushare-downloader refresh daily_basic -s 2024-01-02 -e 2024-01-02 --max-age 0
uv run tushare-downloader u stock_basic
```

已有日频数据可用 `u daily_basic` 从本地最新日回看到昨日；历史较旧时可能产生很多请求，
可先加 `--dry-run` 查看计划。fetch 按成功检查记录跳过，refresh 按核对年龄选择，
update 不跳过回看窗口。快照不接受日期参数。

配置从当前目录 .env 或 -c 指定文件读取，环境变量优先。密码与 Token 不提交。
日志写入 logs/，完整前后报告写入 reports/；可用 --plain 关闭动态显示。

支持分段原子入库、有限重试、同键去重、stale 标记和显式确认的清理。
没有后台任务、status 或 resume。独立日期块失败后已提交数据保留；快照必要请求失败不合并。

设计版本 v0.1.0-draft.12 与软件独立递进。当前软件 0.1.0 仍处开发阶段，
116 项本地测试、故障注入、分层及完整流程 benchmark、主分支 CI 和 Pages 回退已通过；
PR 触发验证及必需检查设置尚待完成，详见验收记录。
