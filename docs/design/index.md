# 设计文档

**交付目标：v0.4.0 · 设计 revision 2 · 状态：定稿。** 已发布软件基线：v0.3.0；发布时间由维护者决定。
本次修订共用交付版本号及设计 revision 管理规则，并按维护者要求起草 Inspect 与用户数据访问规范（含公开 schema 契约），维护者已确认定稿并授权本地实施。现有候选实现依据上一份已定稿设计 design-v0.4.0（逻辑 revision 1）；不因本次草案而改变历史验收归属。新增能力尚未实现，不能沿用原候选结论宣称扩展范围已验收。

本轮纳入 BL-014 工作流、BL-010 日志目录、BL-011 升级指南及 BL-017 development 版本产物目录整理；本次草案增加 BL-012 Inspect 与 BL-013 schema，已进入 working，开始按已定稿设计测试先行实施。本次进一步新增 BL-018 数据库设置向导，归入同一定稿范围与 working。历史定稿由 design-v0.3.0 标签保留；v0.3.0 已通过软件验收并发布。

## 阅读导航

| 内容 | 规范来源 |
| --- | --- |
| 设计先行、测试先行与版本迭代 | [开发工作流草案](workflow.md) |
| 按命令分目录、旧日志兼容与测试条件 | [日志目录](log-layout.md) |
| 连接、账号、初始化与升级检查的统一交互 | [数据库设置向导](database-setup.md) |
| 旧用户升级路线、验证与恢复 | [升级指南设计](upgrading.md) |
| development 版本归档、旧链接兼容与迁移验证 | [版本产物目录](development-layout.md) |
| 本地空间、最新日期、最近拉取与只读呈现 | [Inspect](inspect.md) |
| 只读账号、标准 SQL、stale 读取与可选视图 | [用户数据访问](data-access.md) |
| 数据访问子章节：表结构、版本映射与兼容性 | [schema 契约](schema-contract.md) |
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

当前完整设计只维护一套，各章节共享入口版本；历史正文由 Git 提交和定稿标签保存。采用共用交付版本号，设计另记 revision 与草案／定稿状态；具体规则和过渡方式见 [工作流第 6 节](workflow.md)。

完整修订记录、版本规则和历史归档见 [设计变更记录](changelog.md)。

当前实施基线：本地标签 `design-v0.4.0`（逻辑 revision 1，尚未推送）。本次 revision 2 已定稿，新实施基线为本地 design-v0.4.0-r2；原标签及证据不变。

上一版定稿标签：[design-v0.3.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.3.0/docs/design)。设计定稿不代表目标软件已实现、验收或发布。

当前实施进展见 [revision 2 本地记录](../development/releases/v0.4/v0.4.0/revision-2/index.md)。各章“尚未实施”描述定稿时状态，不作为当前软件完成声明；验收与发布独立记录。
