# tushare-downloader

将 Tushare Pro 数据下载到 PostgreSQL，每个 API 对应一张原始数据表。
当前实现支持 `daily_basic` 和 `stock_basic`，提供范围补齐、强制核对、增量更新、进度和完整报告。

软件版本为 0.1.0。验证范围与证据见[验收记录](development/acceptance.md)。

| 你的目的 | 从这里开始 |
| --- | --- |
| 第一次安装、连接数据库并下载 | [快速开始](guide/quickstart.md) |
| 设置 Token、连接和输出偏好 | [配置](guide/configuration.md) |
| 选择 fetch、refresh 或 update | [下载与报告](guide/downloading.md) |
| 查命令、选项和支持接口 | [CLI 参考](reference/cli.md)、[API 参考](reference/apis.md) |
| 管理数据库和备份 | [数据库运维](operations/database.md)、[备份与恢复](operations/backup-restore.md) |
| 开发、测试和性能测量 | [开发环境](development/setup.md)、[测试](development/testing.md)、[Benchmark](development/benchmarks.md) |
| 理解设计决策和算法 | [设计文档](design/index.md) |

使用指南描述当前实现；设计正文保留原版本和内容，不作为全部功能已经验收的声明。
Excel Power Query 是[可选使用演示](guide/excel.md)，不是验收门槛。
