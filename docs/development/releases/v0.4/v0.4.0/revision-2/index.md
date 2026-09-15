# v0.4.0 revision 2 本地实现记录

设计已由维护者定稿并授权实施。软件仍是本地候选，没有推送、创建软件标签或发布。

- 定稿标签：design-v0.4.0-r2；设计 SHA：`b09fd662c34540ac876e039eba28bff3ad860db6`。
- 本次实现候选：`3bb9354f743bd1f2bcbe315d34aa02e02c6c5720`；原候选记录保持原归属。
- 新能力：schema 离线契约、inspect 只读查询、setup 连接/初始化/升级检查和分步脚本。
- 数据库结构：六张 raw 表及 meta 保持既有结构；精度和对象类型验证加强；没有通用迁移引擎。

## 已执行的验证

| 验证 | 结果与证据 |
| --- | --- |
| 测试先行 | 新命令 12 项、向导计划/保存 12 项预期失败；[CLI](test-first-cli.txt)、[setup](test-first-setup.txt) |
| 完整本地回归 | 327 passed，含 unit/integration/cluster；[记录](regression.txt) |
| 标准旧库 | 实际 v0.3.0 源码在独立 tushare_test 中建立六表 active/stale 与观察记录；候选重复 init-db 后逐表 JSON 快照不变，SHA256 `7bd0621a6714d825cc7ad9e9e53c68a0aab46cac400754760a36d687c10164ad` |
| 只读权限 | 独立随机 tdw_* 库/角色中验证 SELECT、视图读取，以及写入/DDL 拒绝；测试位于 tests/cluster |
| 导出包 | 实际 psql 执行已有角色路线，Bash 初始化固定目标；即使 PGDATABASE 被外部环境设置为错误值，也不访问错误库 |
| 发行包 | wheel/sdist 构建与独立安装；schema、inspect/setup 帮助可用；[记录](distribution.txt) |
| 实际 Inspect | [输出](inspect-smoke.txt)：空/非空、stale 行计数与观察时间；UTC 格式另有回归测试 |
| 文档 | 严格构建、schema reference 漂移检查、131 历史路径与 6101 相对链接检查通过 |

数据库环境为 WSL Python → Windows PostgreSQL 18 的临时 55433 集群；未修改正式 5432 数据库或用户 .env。实例级测试独立于通常的 integration CI 入口，要求显式管理员 URL、实际 data_directory 校验及 psql 路径。

## Inspect 性能观察

合成 tushare_bench 数据，1,000 与 100,000 行，各场景五轮，包含子进程和连接开销；[原始数据与查询计划](inspection-benchmark.json)。性能数据采于读取实现相同、后续仅呈现/权限诊断修正前，不宣称其他规模恒定延迟。

| 行数 | stale 密集 | 精确计数 | 中位数 | 最小–最大 |
| --- | --- | --- | --- | --- |
| 1000 | False | False | 0.175s | 0.158–0.190s |
| 1000 | False | True | 0.165s | 0.152–0.179s |
| 1000 | True | False | 0.152s | 0.149–0.159s |
| 1000 | True | True | 0.157s | 0.153–0.165s |
| 100000 | False | False | 0.155s | 0.146–0.159s |
| 100000 | False | True | 0.161s | 0.156–0.171s |
| 100000 | True | False | 0.187s | 0.181–0.200s |
| 100000 | True | True | 0.219s | 0.214–0.226s |

## 验收边界与剩余工作

本记录不将 IN/SC/DA/DBW 的所有子条件逐项标为通过。当前回归覆盖核心路径，但尚不能据此宣布全部 revision 2 验收完成。

- 真实终端 40/80/120 列的人工体验、隐藏输入和取消流程：待用户确认。自动交互分支测试不能代替人工签核。
- 导出包的新角色交互密码设置需要真实终端体验；自动 psql 演练覆盖已有角色路线，未伪称验证全部认证方式。
- BL-017 原有浏览器旧链接/query/hash 与窄屏签核仍按原记录待收尾。
- 对全部 DBW 故障矩阵和继承权限变化还需逐项审计；已有 327 测试不等于完成每条复合验收条件。
- 本次没有真实 Tushare 请求；下载协议未变，复用原证据的范围限于该未变部分。
- 远端 CI/Pages 及正式发布检查未执行；仍需人类明确提出发布。

BL-012、BL-013、BL-018 保持 working，表示实现已落地、验收仍在收尾；不因功能存在就标 completed。

最终补充：拒绝无法无损改写的多行配置，防止其中类似 PG* 的文本被误改；完整 327 项回归与发行包检查已针对该修复重新执行。旧库/性能证据涉及的数据读取和结构逻辑未受此配置修复影响，按此边界复用。
