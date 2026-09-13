# 实现验证记录

2026-09-14：两个接口的实现、116 项本地测试、分层与完整流程 benchmark、主分支 CI 和 Pages 回退已验证。剩余 PR 验证与仓库必需检查设置见[验收记录](acceptance.md)。

## 本地验证

- Windows PostgreSQL 18：独立 55432 测试实例，数据库与账号均为 tushare_test。
- 集成场景：重复初始化、结构损坏拒绝接管、唯一约束失败回滚、NULL 覆写、stale/恢复、双实例互斥、外键阻止清理。
- 执行场景：中间日期失败保留已提交块、重跑只补失败日期、快照必要请求失败不合并、dry-run 不写库、提交未知停止。
- 输出场景：长报告终端省略但文件保留全量，JSONL 轮转保留全部事件。
- 真实接口：daily_basic 的 2024-01-02 返回并保存 5,329 行，重复 fetch 跳过；stock_basic 五种状态合计返回并保存 5,911 行。
- 真实数据库 tushare 已初始化；没有做历史全量下载，也没有物理清理正式数据。

字段与请求范围依据 [daily_basic 官方说明](https://tushare.pro/document/2?doc_id=32)、
[stock_basic 官方说明](https://tushare.pro/document/2?doc_id=25)；
事务实现参照 [Psycopg 事务文档](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)。

stock_basic 各状态是一个快照的分区，允许个别状态成功返回空集；
五个必要请求均成功且总集合非空时才允许核对缺失键。总集合为空时保留旧行并报告待核实。
每个分区检查返回的 list_status 与请求一致；跨分区同键冲突整段失败。
两个接口已启用核对能力，协议成功仍不等于源端业务完整性证明。

## 进度、报告与 Benchmark 补充

- 进度线程只负责展示：HTTP、限速、重试和数据库操作期间持续刷新。
- 分开显示已取得/暂存与已确认入库输入行，显示 HTTP 与入库速率。
- ETA 使用最近最多 20 个完整逻辑块；至少 5 个样本且合计 10 秒才显示。退避、提交阶段和异常长耗时时隐藏估计。
- 报告摘要不截断，各分类分别限制终端条数；只合并原因相同且日期相邻的范围。完整 Markdown 保留每个分段。
- Rich 进度条与详情分行，窄终端可换行；plain 无 ANSI。输出结束前停止刷新线程。
- 日志增加请求范围、阶段诊断与 HTTP/解析/限速/重试/数据库/报告耗时。
- 三层 benchmark 已分别实跑，每场景至少 5 次；见[指南](benchmark.md)和[基准记录](benchmark-baseline.md)。

## 后续验证

- 用户已确认取消 Windows 原生 Python 验收；本版覆盖 WSL/Linux Python，数据库服务可运行于 Windows。GitHub CI/CD 结果见验收记录。
- 当前 benchmark 是固定规模的分层基准；更大数据规模、长时间运行及不同机器之间的比较按实际需要扩展。
- 故障测试矩阵继续补充，不把有限代表用例当作对所有输入的证明。

本轮补齐结果见[验收记录](acceptance.md)。
