# 设计文档

**交付目标：v0.4.0 · revision 7 定稿（体验反馈与错误指引）。已定稿并完成本地实施验收。**

本轮 BL-021 处理 [三次体验](../development/releases/v0.4/v0.4.0/user-experience/index.md) 中的五类问题，行为规范已合并到日志、报告与帮助、setup 章节；UX01–UX07 统一见 [验收 R 节](acceptance.md#revision-7)，[修订与评审记录](../development/releases/v0.4/v0.4.0/revision-7/design-review.md)说明来源与取舍。定稿评审已完成并补齐阶段、状态与验证边界；维护者已确认定稿并授权测试先行实施。

已实现基线为 revision 7，软件尚未发布；[最终本地验收](../development/releases/v0.4/v0.4.0/final-acceptance/index.md)及后续文档提交是历史候选证据，revision 7 当前结果见 [实施验收](../development/releases/v0.4/v0.4.0/revision-7/index.md)。原 suspend_d 请求预算偏差及接受决定保留原记录。

## 从哪里开始

- **第一次了解项目**：先读 [总体设计](overview.md)，再按要研究的功能进入下方分组。
- **评审当前 revision 7**：从 [修订索引](../development/releases/v0.4/v0.4.0/revision-7/design-review.md)进入日志、帮助/报告和 setup 共用规范，再核对 [UX01–UX07](acceptance.md#revision-7)。迁移规则仍见 [迁移契约](database-migrations.md)，不作为本轮新增验证范围。
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

当前已实施设计基线为本地 `design-v0.4.0-r7`（`5925e8a`）；revision 5 实现提交 `d79ba31` 保留历史。历史设计标签不移动，旧验收保留原归属。

上一已发布软件的设计标签：[design-v0.3.0](https://github.com/laiyk5/tushare-downloader/tree/design-v0.3.0/docs/design)。验收和发布独立记录。

当前实现证据见 [revision 6](../development/releases/v0.4/v0.4.0/revision-6/index.md)。本页与各当前章节描述目标设计，历史行为查 Git 标签，不能把旧状态注释当成当前交付状态。

revision 6 已完成本地实施与验收，软件仍未发布；见 [验收记录](../development/releases/v0.4/v0.4.0/revision-6/acceptance.md)。
