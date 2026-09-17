# 设计文档

**交付目标：v0.4.0 · revision 6 定稿并实施（setup 顺序版本迁移与开发数据库约定）。** 已发布软件基线：v0.3.0；发布时间由维护者决定。

本轮范围为 BL-020：将独立迁移入口并入 setup，按现有数据库版本连续执行迁移，并明确可重置开发库与生产正式代码访问约定。Click 顺序问答、Rich/plain 及其他未改变业务规则继承既有设计。**revision 6 已定稿，维护者授权测试先行实施。**

revision 5 已实施并按现有功能证据验收；请求预算偏差经维护者接受并保留记录。见 [实施与验收记录](../development/releases/v0.4/v0.4.0/revision-5/index.md)。软件尚未发布。

当前定稿：[Setup 版本迁移与数据库环境](database-migrations.md)，验收条件见 [MG01–MG08](acceptance.md#revision-6)。本次定稿行为按测试先行实施。

## 从哪里开始

- **第一次了解项目**：先读 [总体设计](overview.md)，再按要研究的功能进入下方分组。
- **评审当前 setup 修订**：按 [执行契约](database-setup.md) → [交互界面](database-setup-ui.md) / [headless](database-setup-headless.md) → [迁移契约](database-migrations.md) → [验收标准 Q 节](acceptance.md#revision-6) 阅读；[Demo](database-setup-demo.md)辅助理解，不替代规范。
- **准备实施或核对完成情况**：先看 [开发工作流](workflow.md) 与 [验收标准](acceptance.md)，实际执行证据在 development 的版本记录中。

## 按主题阅读

下列分组与 Zensical 侧栏一致。通用规则、功能契约、交互示例和开发记录各有入口，不将每份新文档继续追加到同一层。

| 分组 | 内容 |
| --- | --- |
| 总体与约定 | [总体设计](overview.md)、[配置约定](configuration.md)、[语言规范](language-policy.md) |
| 数据与下载 | [数据集与 API 契约](research-datasets.md)、[请求规划与过滤](request-planning.md) |
| 数据库与数据访问 | [读取方式与权限](data-access.md)、[schema 契约](schema-contract.md)、[Inspect](inspect.md)、[升级与兼容](upgrading.md) |
| 数据库设置（setup） | [职责与执行契约](database-setup.md)、[版本迁移](database-migrations.md)、[交互界面](database-setup-ui.md)、[headless 自动化](database-setup-headless.md)、[向导 Demo](database-setup-demo.md) |
| CLI 输出与报告 | [输出与进度](cli-experience.md)、[帮助与报告契约](help-and-reports.md)、[日志目录](log-layout.md)、[输出 Demo](cli-demo.md)；报告样例见 [日频](examples/report-example.md)、[快照](examples/report-snapshot-example.md)、[执行前计划](examples/report-plan-example.md) |
| 开发、验收与历史 | [工作流](workflow.md)、[验收标准](acceptance.md)、[版本产物目录](development-layout.md)、[变更记录](changelog.md) |

总体设计定义通用业务规则，专章定义各功能细节。数据库访问规范定义用户可依赖的读取方式，setup 定义如何配置这些能力，两者不重复维护权限规则。Demo 和报告样例是说明材料，不是独立契约。

### 组织约定

新增章节优先进入现有主题；只有独立且持续扩展的主题才新增分组。同一页面只在侧栏出现一次，用正文链接关联其他主题；例子放在对应功能下，不与主契约平铺。导航标题不带草案/定稿字样，版本状态统一看本页和正文，避免定稿后出现过期标题。

文档整理保留已有 Markdown 页面 URL；新增迁移章归入 setup 分组。导航分组不要求同名实体目录；若后续确需迁移文件，另做链接及旧 URL 兼容，避免为了目录外观搬动全部文件。

## 版本与历史

当前完整设计只维护一套，各章节共享入口版本；历史正文由 Git 提交和定稿标签保存。采用共用交付版本号，设计另记 revision 与草案／定稿状态；具体规则和过渡方式见 [工作流第 6 节](workflow.md)。

完整修订记录、版本规则和历史归档见 [设计变更记录](changelog.md)。

当前已实施设计基线为本地 `design-v0.4.0-r6`（`225eef2`）；revision 5 实现提交 `d79ba31` 保留历史。历史设计标签不移动，旧验收保留原归属。

上一已发布软件的设计标签：[design-v0.3.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.3.0/docs/design)。验收和发布独立记录。

当前实现证据见 [revision 6](../development/releases/v0.4/v0.4.0/revision-6/index.md)。本页与各当前章节描述目标设计，历史行为查 Git 标签，不能把旧状态注释当成当前交付状态。

revision 6 已完成本地实施与验收，软件仍未发布；见 [验收记录](../development/releases/v0.4/v0.4.0/revision-6/acceptance.md)。
