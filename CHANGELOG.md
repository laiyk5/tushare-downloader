# Changelog

## v0.4.0 — 2026-09-18

- Add guided/headless database setup and ordered migrations through setup.
- Correct suspend_d event keys; preserve existing data through the supported migration.
- Add dataset inspection, documented reader access and stable schema contracts.
- Group logs by command and improve failure reports, setup results and CLI help.
- Document upgrades and organize development evidence by version.

See [release notes](docs/development/releases/v0.4/v0.4.0/release.md) and the [upgrade guide](docs/operations/upgrading.md).

## Early development notes (historical)

- 项目骨架、独立开发环境和设计文档迁入。
- 配置 Zensical、GitHub Pages 工作流与基础 CI。
- 配置读取、API 定义、固定块规划、HTTPS 限速/重试和类型解析。
- 接通 init-db、fetch/f、refresh、update/u、list/ls、clean。
- PostgreSQL COPY/staging、upsert、stale/恢复、原子检查记录及数据库写实例锁。
- 前后 Markdown 报告、JSONL 日志及基础 Rich/plain 进度。
- 独立 PostgreSQL 集成测试和小范围真实 Tushare 入库验证。
- 持续完善故障验证矩阵；软件尚未正式发布。

- 补充 benchmark 五次重复采样、阶段计时与本机基准记录；报告合并相邻范围并保留全量文件。
