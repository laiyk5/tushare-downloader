# 设计文档

**当前设计：v0.4.0** · 已发布软件基线：v0.3.0。本轮范围为下列四项 working；目标软件 v0.4.0，发布时间由维护者决定。
本目录维护当前完整设计；继承 v0.3.0 的业务规范，本轮新增开发工作流、日志目录、升级指南与版本产物目录规范，已由维护者确认定稿。验收章节保留既有业务门槛并加入当前 working 条件；目标软件为 v0.4.0，尚未发布，不表示整个 backlog 已纳入。

本轮纳入 BL-014 工作流、BL-010 日志目录、BL-011 升级指南及 BL-017 development 版本产物目录整理；BL-012 Inspect 与 BL-013 schema 仍排队，不在本轮实施范围。历史定稿由 design-v0.3.0 标签保留；v0.3.0 已通过软件验收并发布。

## 阅读导航

| 内容 | 规范来源 |
| --- | --- |
| 设计先行、测试先行与版本迭代 | [开发工作流草案](workflow.md) |
| 按命令分目录、旧日志兼容与测试条件 | [日志目录](log-layout.md) |
| 旧用户升级路线、验证与恢复 | [升级指南设计](upgrading.md) |
| development 版本归档、旧链接兼容与迁移验证 | [版本产物目录](development-layout.md) |
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

当前定稿标签：[design-v0.4.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.4.0/docs/design)（本地建立，尚未推送）。

上一版定稿标签：[design-v0.3.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.3.0/docs/design)。设计定稿不代表目标软件已实现、验收或发布。
