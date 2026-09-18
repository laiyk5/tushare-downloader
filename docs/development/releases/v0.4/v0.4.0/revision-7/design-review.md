# Revision 7 design review

Status: draft, reviewed; not implemented. Target remains v0.4.0.
Source: [three bounded experience sessions](../user-experience/index.md), backlog BL-021.
This record explains the revision and review; normative text lives in the topic chapters.

| Scope | Canonical document |
| --- | --- |
| Failure event, safe description and stage boundaries | [Logging](../../../../../design/log-layout.md#preparation-errors) |
| Failure report, option guidance, dataset descriptions and quiet help | [Help and reports](../../../../../design/help-and-reports.md#preparation-report) |
| Ready, login checks and configuration-save explanation | [Setup](../../../../../design/database-setup.md#result-explanation) |
| UX01–UX07 and bounded validation | [Acceptance R](../../../../../design/acceptance.md#revision-7) |
| Feedback intake and document ownership | [Workflow](../../../../../design/workflow.md#feedback-intake) |

The five experience findings are retained in their original reports. No product code, schema,
request policy or privilege checks change during this document reorganization.
The following is the Chinese design-review record, retained as review rationale rather than a second specification.

## 7. 评审结论与边界

上述变更不改变下载范围、数据库结构、权限或认证政策，无迁移要求；仅增补日志错误事件和调整人类可读输出。
List 默认文本布局会变化，但 API 名和离线用途保持，未承诺按终端行格式提供机器协议。
本稿等待维护者定稿；revision 6 的本地验收只证明原候选，不证明本修订已实施。此稿成为 v0.4.0 目标的新修订后，最终发布需采用实施本稿后的候选证据。


### 2026-09-18 定稿评审

结论：补齐本轮五项边界后，设计合理、自洽且可执行，UX01–UX07 对应五项体验问题及文档交付，无必须增加的真实平台测试；**可交维护者确认定稿**，尚未授权实施。

| 审查点 | 原缺口 | 收口结果 |
| --- | --- | --- |
| 请求事实 | 准备失败容易被误写成所有 HTTP 均为零 | 区分日历与数据尝试；未知不填零；执行失败不改归类 |
| 状态文案 | not_saved 无法唯一推出 no save needed | 按失败、保存、未保存修改、沿用顺序选择；保留环境覆盖与失败验证事实 |
| 选项纠错 | 直接拼命令可能泄露值，短选项与同名选项边界未定 | 使用注册信息与占位值；限定普通未知选项错误分支，不重解析或执行 |
| 验证完整性 | 缺日志级别、dry-run、日历尝试、保存覆盖案例 | 在既有 UX 编号补齐，明确合法级别及有限等价类 |
| 验证重复 | 模式×宽度×故障容易膨胀 | 固定代表组合，共用故障夹具、一个 PTY 和一个安装环境 |

该评审是文档结论，不是软件验收结果；无需为评审运行产品回归或外部 API。
