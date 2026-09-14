# 设计文档

**当前设计：v0.2.0-draft.7** · 草案，尚未定稿。目标软件：v0.2.0。
这是当前完整设计，阅读时无需拼接 v0.1.0 或之前草案。软件新功能是否实现以验收记录为准。

## 阅读导航

| 内容 | 规范来源 |
| --- | --- |
| 目标、命令、数据、事务、运维、测试与发布 | [总体设计](overview.md) |
| 配置加载、分组模板、忽略规则 | [配置设计](configuration.md) |
| 固定块算法、本地跳过与交易日过滤 | [请求规划](request-planning.md) |
| Rich/plain、信息量、进度与日志展示 | [CLI 体验](cli-experience.md) |
| 帮助、单文件报告生命周期及格式 | [帮助与报告](help-and-reports.md) |
| 静态模板 | [日频报告](examples/report-example.md)、[快照报告](examples/report-snapshot-example.md)、[初始计划](examples/report-plan-example.md) |
| 可交互展示 | [CLI Demo](cli-demo.md) |

核心业务规则由总体设计定义；帮助页中的接口对照用于展示，其描述应与总体设计一致。示例不是独立规范。

## 版本与历史

当前完整正文只在 docs/design/ 维护一套。历史用 Git 提交和标签保存，不创建每版目录。
软件标签 vX.Y.Z 与设计定稿标签 design-vX.Y.Z 分开；草案通常不打标签。各章节共享入口版本，不重复维护章节版本号。
每轮完整修订递增 draft.N；发布过的提交可追溯，不改写历史。此轮只整理 v0.2.0，尚未补录 v0.1.0 的设计定稿标签。

- [软件 v0.1.0 当时保存的设计](https://github.com/laiyk5/tushare-downloader/tree/v0.1.0/docs/design)：正文当时标为 draft.12，保留真实历史，不将其冒充已建立的设计标签。
- [整合前 v0.2.0-draft.6](https://github.com/laiyk5/tushare-downloader/tree/a04b719/docs/design/v0.2.0)：旧的增量文档仅作历史记录。
- [软件验收记录](../development/acceptance.md)。

## 修订记录

| 版本 | 内容 |
| --- | --- |
| v0.2.0-draft.1 | 纳入配置整理、读者分层文档、英文交互与帮助、日历过滤、许可证决策流程；保留市场覆盖验证门槛 |
| v0.2.0-draft.2 | 整体定义 Rich/plain、quiet/normal/verbose、最近日志、输出流及降级行为 |
| v0.2.0-draft.3 | 补充帮助 Examples、紧凑单文件报告与异常终止语义 |
| v0.2.0-draft.4 | 核对两个 API 的六种命令语义，补齐快照子请求与四类写入统计 |
| v0.2.0-draft.5 | 默认基础交易日过滤、可选在线日历与主动绕过；取消自动降级，补充配置整理方案 |
| v0.2.0-draft.6 | 确认配置与 gitignore 完整模板、注释规范及开发环境连接边界 |
| v0.2.0-draft.7 | 整合为单一完整设计，统一目录、示例与导航；历史由 Git 保存 |
