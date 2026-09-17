# 设计文档

**交付目标：v0.4.0 · revision 4 已定稿；revision 5 定稿（数据契约修正、验收机制及 Inspect 总览）。** 已发布软件基线：v0.3.0；发布时间由维护者决定。

本次针对 BL-018 将全屏 Textual 交互替换为 Click 顺序问答和 Rich 语义配色：自动检查、编号修改、差异确认、失败重查及独立保存。保留共用数据库核心与 headless；支持同流程 plain，新增交互 --new。其他未改变规则继承既有定稿。维护者已授权实施，按本次定稿及 O.4 范围测试先行，不回档产品代码。

本轮已有范围为 BL-010/011/012/013/014/017/018；队列及完成情况以 backlog 为准。revision 2 已有本地候选实现，发现的认证问题与修复保留原始记录，不将旧测试结果冒充 revision 3 验收。

revision 5 已实施并按现有功能证据验收；请求预算偏差经维护者接受并保留记录。见 [实施与验收记录](../development/releases/v0.4/v0.4.0/revision-5/index.md)。软件尚未发布。

## 从哪里开始

- **第一次了解项目**：先读 [总体设计](overview.md)，再按要研究的功能进入下方分组。
- **评审当前 setup 修订**：按 [执行契约](database-setup.md) → [交互界面](database-setup-ui.md) / [headless](database-setup-headless.md) → [验收标准 O 节](acceptance.md) 阅读；[Demo](database-setup-demo.md)辅助理解，不替代规范。
- **准备实施或核对完成情况**：先看 [开发工作流](workflow.md) 与 [验收标准](acceptance.md)，实际执行证据在 development 的版本记录中。

## 按主题阅读

下列分组与 Zensical 侧栏一致。通用规则、功能契约、交互示例和开发记录各有入口，不将每份新文档继续追加到同一层。

| 分组 | 内容 |
| --- | --- |
| 总体与约定 | [总体设计](overview.md)、[配置约定](configuration.md)、[语言规范](language-policy.md) |
| 数据与下载 | [数据集与 API 契约](research-datasets.md)、[请求规划与过滤](request-planning.md) |
| 数据库与数据访问 | [读取方式与权限](data-access.md)、[schema 契约](schema-contract.md)、[Inspect](inspect.md)、[升级与兼容](upgrading.md) |
| 数据库设置（setup） | [职责与执行契约](database-setup.md)、[交互界面](database-setup-ui.md)、[headless 自动化](database-setup-headless.md)、[向导 Demo](database-setup-demo.md) |
| CLI 输出与报告 | [输出与进度](cli-experience.md)、[帮助与报告契约](help-and-reports.md)、[日志目录](log-layout.md)、[输出 Demo](cli-demo.md)；报告样例见 [日频](examples/report-example.md)、[快照](examples/report-snapshot-example.md)、[执行前计划](examples/report-plan-example.md) |
| 开发、验收与历史 | [工作流](workflow.md)、[验收标准](acceptance.md)、[版本产物目录](development-layout.md)、[变更记录](changelog.md) |

总体设计定义通用业务规则，专章定义各功能细节。数据库访问规范定义用户可依赖的读取方式，setup 定义如何配置这些能力，两者不重复维护权限规则。Demo 和报告样例是说明材料，不是独立契约。

### 组织约定

新增章节优先进入现有主题；只有独立且持续扩展的主题才新增分组。同一页面只在侧栏出现一次，用正文链接关联其他主题；例子放在对应功能下，不与主契约平铺。导航标题不带草案/定稿字样，版本状态统一看本页和正文，避免定稿后出现过期标题。

这次只整理信息架构和阅读入口，保留 Markdown 文件位置、已有页面 URL 和正文规则。导航分组不要求同名实体目录；若后续确需迁移文件，另做链接及旧 URL 兼容，避免为了目录外观搬动全部文件。

## 版本与历史

当前完整设计只维护一套，各章节共享入口版本；历史正文由 Git 提交和定稿标签保存。采用共用交付版本号，设计另记 revision 与草案／定稿状态；具体规则和过渡方式见 [工作流第 6 节](workflow.md)。

完整修订记录、版本规则和历史归档见 [设计变更记录](changelog.md)。

当前实施基线仍是本地 design-v0.4.0-r3；revision 4 已获维护者实施授权，定稿基线记录为 design-v0.4.0-r4；不移动旧标签。revision 1/2/3 及其验收证据均保留原归属。

上一版定稿标签：[design-v0.3.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.3.0/docs/design)。设计定稿不代表目标软件已实现、验收或发布。

当前实施进展见 [revision 4 本地记录](../development/releases/v0.4/v0.4.0/revision-4/index.md)；[revision 3](../development/releases/v0.4/v0.4.0/revision-3/index.md) 保留历史来源。各章“尚未实施”描述定稿时状态，不作为当前软件完成声明；验收与发布独立记录。


新增 [API 契约调查与 suspend_d 修正](api-contract-validation.md)：记录真实反例、调研及验收漏洞、拟议新键和迁移门槛。合并范围已获维护者确认定稿；按本轮补齐的迁移、Inspect 及验收条件评审，不改写 revision 4 定稿标签。
