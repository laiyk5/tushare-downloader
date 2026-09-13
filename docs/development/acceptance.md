# v0.1.0 验收记录

状态：本地验收已完成，正在执行真实 GitHub CI/CD 与 Pages 验收。正式发布尚未声明。

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
| GitHub Actions / Pages / 回退 | 等待真实工作流和站点验证，完成后补链接 | 待验证 |

本轮本地结果为 116 项测试通过。覆盖率不是单独的发布门槛。
新增测试不承诺证明所有输入正确；首版源端 API 成功仍不等于业务完整性证明。

Excel 为可选使用演示，不是验收门槛。
.env/.gitignore 的结构化分组仍在下一轮设计待办中，不在本轮改动范围。
