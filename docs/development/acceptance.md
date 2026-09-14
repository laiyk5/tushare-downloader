# v0.1.0 验收记录

状态：v0.1.0 验收通过。软件功能与仓库流程分别核对，当前两类门槛均已完成；验收不等同于已发布安装包或创建 Release。

验收范围：WSL/Linux Python；本机数据库是 Windows PostgreSQL 18。
Windows 原生 Python 根据用户确认移出本版范围。软件版本与设计版本独立，
本次设计修订为 v0.1.0-draft.12。

| 设计要求 | 证据 | 状态 |
|---|---|---|
| 命令 × 数据变化 × 查询形态 | test_acceptance_matrix.py 的 12 个组合；无源端全集边界的可变时间型 update 明确拒绝 | 本地通过 |
| 配置/CLI/规划/解析 | unit、CLI 集成与已有真实 API 样本 | 本地通过 |
| 初始化/权限边界/清理 | 专用数据库、外部对象拒绝接管、主键/列校验、外键阻止清理、实例锁 | 本地通过 |
| 分段事务、stale、恢复与计数 | storage/snapshot/download 集成测试 | 本地通过 |
| COMMIT 确认丢失 | TCP 代理分别在 COMMIT 前断开、服务器完成提交后丢弃回复；重新连接确认原子事实及安全重发 | 本地通过 |
| 连接终止与 Ctrl+C | pg_terminate_backend 真正终止数据库会话；事务内中断回滚及请求中断退出 130 | 本地通过 |
| 输出失败不破坏提交 | 日志写入 /dev/full 产生真实 I/O 错误；已提交数据保留、后续请求停止、非零退出 | 本地通过 |
| 进度/ETA/报告 | 守恒、零分母、暂停 ETA、窄屏、Rich/plain、长报告和原子文件写出测试 | 本地通过 |
| 完整流程 benchmark | benchmarks/flow.py：假 HTTP + 真实 PostgreSQL + 日志/报告，12 场景各 5 次 | 本地通过 |
| 分层 benchmark | 本地处理、数据库写入、真实 API，原始样本与环境保留 | 本地通过 |
| GitHub Actions 主分支 | Ubuntu Python 单元测试、真实 PostgreSQL 18 密码认证集成测试、Ruff、wheel 安装验证 | 通过 |
| Pages 部署 / 回退 | 主分支构建部署，线上标记出现，再 git revert 后消失 | 通过 |
| Pages 页面 / 资源 / 搜索 | 16 个页面及直接引用资源 HTTP 200；浏览器搜索 benchmark 得到结果 | 通过 |
| PR 触发 / 必需检查 | PR #1 的 Checks 与 docs-build 通过，deploy 跳过；main 已设置 GitHub Actions 的 docs-build 必需检查 | 通过 |
| 最新文档合并与部署 | PR #1 已合并；25 个页面及引用资源通过，新增快速开始可搜索 | 通过 |

本轮本地结果为 116 项测试通过。覆盖率不是单独的发布门槛。
新增测试不承诺证明所有输入正确；首版源端 API 成功仍不等于业务完整性证明。

Excel 为可选使用演示，不是验收门槛。
.env/.gitignore 的结构化分组仍在下一轮设计待办中，不在本轮改动范围。

## GitHub 实际运行证据

- 仓库：[laiyk5/tushare-downloader](https://github.com/laiyk5/tushare-downloader)。
- 实现修复提交 b15b80b：[Checks 成功](https://github.com/laiyk5/tushare-downloader/actions/runs/34772433926)、[Pages 成功](https://github.com/laiyk5/tushare-downloader/actions/runs/34772433917)。
- 回退演练：提交 65acefa 发布临时标记，[部署成功](https://github.com/laiyk5/tushare-downloader/actions/runs/34772567209)，在线页面确认出现标记；随后提交 cb0eb09 通过 git revert 撤销，重新部署后确认标记消失。
- 站点：[在线文档](https://laiyk5.github.io/tushare-downloader/)。项目子路径、页面及引用资源检查结果保存在本地 reports/pages-validation.json；搜索由浏览器实际验证。

首次远端集成测试暴露测试夹具重连 DSN 丢失密码、故障代理继承 IPv6 地址的问题；
b15b80b 已修复。保留 CI 密码认证，未改成 trust 来规避问题。

## 仓库流程收尾（2026-09-14）

- [PR #1](https://github.com/laiyk5/tushare-downloader/pull/1) 已合并，提交为 8c487af。
- [PR Checks](https://github.com/laiyk5/tushare-downloader/actions/runs/34810321873) 通过；[PR Documentation](https://github.com/laiyk5/tushare-downloader/actions/runs/34810321984) 的 docs-build 成功、deploy 跳过。
- main 的分支保护规则已创建，必需检查为 docs-build，来源限定 GitHub Actions；未要求人工审批或签名提交。管理员保留 GitHub 默认的绕过权限，本次合并在检查通过后执行。
- 合并后的 [Checks](https://github.com/laiyk5/tushare-downloader/actions/runs/34810907639) 与 [Pages 部署](https://github.com/laiyk5/tushare-downloader/actions/runs/34810907665) 均成功。
- 最新站点 25 个页面及引用资源 HTTP 200；浏览器搜索“快速开始”可找到新增指南。完整检查保存在本地 reports/pages-validation-final.json。
- 本次仅完成仓库流程及记录收尾，design/ 的四个文件与 v0.1.0-draft.12 原文保持一致。

功能验收依据前述测试及 API 样本；PR 和分支规则属于工程流程证据，不增加下载器运行能力。
后续 backlog 中的语言、布局、文档写作及交易日历改进不计入本版未完成项。

本轮独立 55432 测试实例已停止并移除。TEST_DATABASE_URL 仅在测试时指向临时专用库，
不会自动连接正式数据库；本轮故障与 benchmark 没有修改正式库。
