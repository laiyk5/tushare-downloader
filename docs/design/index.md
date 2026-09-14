# 设计文档

**当前设计：v0.3.0-draft.1** · 2026-09-15 起草。目标软件：v0.3.0；已发布基线：v0.2.0。
本目录维护当前完整设计，保留既有规范并整合本版章节，无需拼接旧版本。草案尚未定稿，新增 API 契约待验证，不表示功能已经实现。

本轮聚焦中英文范围规范，以及 A 股日频的 daily、adj_factor、stk_limit、suspend_d 扩展，用于验证框架合理性。ETF、财务与指数扩展暂缓。

## 阅读导航

| 内容 | 规范来源 |
| --- | --- |
| 中文、英文及原文例外 | [语言规范](language-policy.md) |
| A 股日频范围、API 契约与框架验证 | [数据集设计](research-datasets.md) |
| 当前设计的验收门槛、证据和发布条件 | [验收标准](acceptance.md) |
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
每轮完整修订递增 draft.N；发布过的提交可追溯，不改写历史。尚未补录 v0.1.0 的设计定稿标签。

- [软件 v0.1.0 当时保存的设计](https://github.com/laiyk5/tushare-downloader/tree/v0.1.0/docs/design)：正文当时标为 draft.12，保留真实历史，不将其冒充已建立的设计标签。
- [整合前 v0.2.0-draft.6](https://github.com/laiyk5/tushare-downloader/tree/a04b719/docs/design/v0.2.0)：旧的增量文档仅作历史记录。
- [软件验收记录](../development/acceptance.md)。

已归档设计：[design-v0.2.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.2.0/docs/design)。已发布软件：[v0.2.0](https://github.com/laiyk5/tushare-downloader/tree/v0.2.0)。当前草案不打定稿标签。演示验证见 [设计定稿记录](../development/design-v0.2.0-finalization.md)。

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
| v0.2.0-draft.8 | 采用 MIT 并声明数据授权边界；统一帮助顺序、进度关闭日志、零请求与报告语义 |
| v0.2.0 | 定稿；同步单文件报告 Demo 与四类写入统计，验证 Zensical 嵌入/六种模式/窄屏，跨日志分片监看移入后续 backlog |

| v0.3.0-draft.1 | 以 v0.2.0 为基线，纳入语言范围和四个 A 股日频 API；明确契约未决项、兼容增表与扩展验收 |
