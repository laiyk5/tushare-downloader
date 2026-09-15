# v0.3.0 实施验收记录（进行中）

本记录不表示整体验收通过。设计基线：`ea630b65c4c99261f3fcf331f3ee2cb800f10d86`（design-v0.3.0）。
实现分支：codex/implement-v0.3.0；最终候选 SHA 尚未确定。门槛见 [验收标准](../design/acceptance.md)。

## 2026-09-15 真实 API 冒烟

软件提交：d9baf49。使用本地配置 Token，通过真实 HTTPS 与执行器写入 Windows PostgreSQL 18 临时实例的专用 tushare_test 库（端口 55433）。
日频请求日期 2026-08-03；stock_basic 请求当前 L/D/P/G/UN 快照。六次命令退出码均为 0。
下表来自 slice_result 日志的本次提交输入行数，不使用可能含早先测试数据的全表行数推断下载量。

| API | 本次提交输入行 | 分段结果 | 本地日志（logs/v03-smoke/） |
| --- | ---: | --- | --- |
| daily_basic | 5529 | success | 20260915T055246Z-3cf5701a.jsonl |
| stock_basic | 5913 | success | 20260915T055248Z-0ec23573.jsonl |
| daily | 5529 | success | 20260915T055254Z-70b2c7d7.jsonl |
| adj_factor | 5549 | success | 20260915T055256Z-6a20f2ed.jsonl |
| stk_limit | 5614 | success | 20260915T055257Z-6a81350f.jsonl |
| suspend_d | 10 | success | 20260915T055259Z-7ff7af57.jsonl |

原始日志与报告位于 Git 忽略目录；不发布授权数据或凭据。以上证明短样本协议、解析与落盘成功，不证明全部历史完整性或 suspend_d 永远唯一。

## 已获得的其他证据

- 598f904：137 项单元与 65 项 PostgreSQL 集成测试通过；新增四接口合并、stale、恢复、空响应保留、增表身份保持及冲突回滚测试。
- d9baf49：开发教程、导航与 benchmark 工具英文范围整理；单元、集成和严格文档构建再次通过。
- 本地 CPU benchmark：benchmarks/results/20260915T055045Z-cf09cc95/，100 行、5 次重复；仅作为本地处理测量，不能替代新增接口端到端比较。

## 尚需完成

新增接口端到端命令/六模式覆盖、benchmark 对照、语言审计清单、发布候选完整回归、分发与第三方材料核对、CI/Pages 及逐项 A–L 签核。
软件版本已进入 0.3.0 实施阶段；未创建软件发布标签，不将设计定稿等同软件验收。

## 候选回归与补充测量

- 65f7726：完整单元与集成合并回归 227 passed，branch coverage 93%；Ruff check/format、构建 Demo iframe 检查、11 项供应方声明核验通过。
- 五个日频 API 的命令矩阵及六模式 × 成功/空/部分失败集成对照通过；见 test_daily_expansion.py、test_output_modes.py。
- 后续补充：四个新增接口 basic/bypass 对照，以及 suspend_d 解析冲突贯穿执行器的整日不写测试；相关 33 项测试通过。最终候选仍需完整重跑。
- 日历 off/basic/cold/hot/bypass/failure 五次重复结果：[汇总](benchmark-v0.3.0-calendar/summary.json)。
- 50 日 × 每日 100 行的输出模式五次重复：[汇总](benchmark-v0.3.0-output/summary.json)。
- 真实 daily_basic 2026-08-03 五次请求测量：[汇总](benchmark-v0.3.0-api/summary.json)。没有数据库写入；不是新增接口历史完整性证明。

## 发布状态

实现分支已推送；GitHub 连接器创建 PR 遇到传输错误，浏览器桥接亦无法连接，尚无 PR/CI/Pages 成功证据。K01/K02/K04 仍未完成，不标记整体验收通过。
存储核心、配置模板、忽略规则、既有 Demo 和 CI/CD 工作流相对 v0.2.0 未改动；历史证据的复用必须在最终索引逐项说明，不能概括代替所有验收。

## 2026-09-15 恢复与真实日历验证

软件 SHA：8dd30c679a81f2f60c2dc6bf4f9430b061be202b。

在临时 PostgreSQL 18 实例（127.0.0.1:55433）创建专用 td_v03_restore_source 和 td_v03_restore_check；源库六张 API 表各写两个合成键，再核对为一个 active、一个 stale。通过官方 pg_dump.exe 的 custom 格式输出和 pg_restore.exe --no-owner --no-privileges --single-transaction --exit-on-error 恢复。
对比六张 raw 表与两个 meta 表的全部行，验证身份、字段类型和主键；专用只读角色可 SELECT 六表，但 INSERT/UPDATE/DELETE 均被拒绝。最后移除本轮两个恢复库和读角色，未操作正式数据库。[脱敏证据](restore-v0.3.0.json)。

真实 trade_cal 请求使用 SSE、20260101–20261231；计划候选为 2026-08-03 起七天。冷缓存一次请求、热缓存零请求，得到相同 5 个请求日和 2 个过滤日；显式绕过不访问日历并保留全部 7 个候选。缓存使用 TemporaryDirectory，验证后清理。[脱敏证据](calendar-live-v0.3.0.json)。

这些结果关闭当前恢复行为和真实日历证据缺口；终端/浏览器人工验证、最终逐项签核和远端 CI/Pages 仍未完成。

## 真实终端补充

[PTY 证据](terminal-v0.3.0/README.md)记录 18 组帮助/列表检查；发现并修复 --plain --help 的 ANSI 泄漏（d46b49d），修复后完整回归 233 passed。静态渲染不代替动态进度或网页浏览器验证。

## 当前结论

本记录上文按时间保留历史未完成项；以 [验收索引](acceptance-index-v0.3.0.md) 的最新逐项签核为准。69 项本地门槛已完成，H04/K01/K02/K04 因浏览器/远端权限尚未完成。软件发布未完成，未创建 v0.3.0 软件标签。
