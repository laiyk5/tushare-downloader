# 设计文档

**当前设计：v0.3.0-draft.2** · 2026-09-15 修订。目标软件：v0.3.0；已发布基线：v0.2.0。
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

当前完整设计只维护一套，各章节共享入口版本；历史正文由 Git 提交和定稿标签保存。设计版本与软件版本独立递进。

完整修订记录、版本规则和历史归档见 [设计变更记录](changelog.md)。
