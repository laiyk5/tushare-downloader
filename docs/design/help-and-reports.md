# 帮助页与完整报告

当前版本见 [设计入口](index.md)。这是拟实现规范，示例为模拟数据。

## 设计判断

帮助页是操作入口：让用户先判断用哪个命令，再找到必要参数，最后复制例子。
不承担设计说明、全部配置字典或实现细节。Examples 应贴近当前命令，而不是重复所有子命令。
完整报告是执行记录：当前模板行距很大、零项重复，视觉负担重但有效信息密度低。
优化目标是紧凑且可查，不是压缩字体或把所有信息挤成一行。

本版合并 before.md / after.md 为单个 `reports/<run>/report.md`。计划与实际结果关联阅读，不要求用户比对两个文件。
JSONL 继续承载按时间排序的事件，不把报告做成实时日志或任务管理系统。

## 帮助页结构

主帮助顺序：Usage → 一句用途 → Commands → Options → Examples → 完整参考链接。
子帮助顺序：Usage → 目的及关键限制 → Options → Examples → 完整参考链接。
参数适用性紧邻命令用途，不能埋在末尾。例如快照禁止日期；只增型 update 使用配置回看，可变型 update 核对完整快照。
主帮助只解释全局选项，子帮助只列自己的选项；Examples 中全局选项始终放在命令前。
每个选项一行主要说明，只有安全边界或取值约束才换行补充。默认来源写成 `config: MAX_AGE; default: 24h`，不读取真实环境。
只展示接口中现有命令、别名及已经实现的选项；新版本发布前再同步新增选项。示例不代表当前 v0.1.0 已支持新参数。

Rich 用清晰的分组、弱化说明、突出命令和选项，不给每一个选项都加面板。
plain 使用同样顺序及文本，不保留边框和颜色；40 列时选项说明换行，不截断命令。
--help 是静态参考：不初始化日志、不读 Token、不查数据库、不请求网络。quiet 不隐藏帮助，verbose 不膨胀帮助。

### 主帮助示意

```text
Usage: tushare-downloader [OPTIONS] COMMAND [ARGS]...

Download Tushare Pro data into PostgreSQL.

Download
  fetch (f)     Fetch a range or snapshot, skipping valid local records.
  refresh       Reconcile a range or snapshot with the source.
  update (u)    Update existing data using the API's update policy.

Database
  init-db (init) Initialize or validate database objects.
  clean         Preview or explicitly apply data cleanup.

Inspect
  list (ls)     List supported APIs.

Options
  -c, --env-file FILE  Configuration file. Default: .env in cwd.
  -q, --quiet          Essential output only.
  -v, --verbose        Include request and diagnostic details.
  --plain              Plain text without terminal controls.
  --version            Show version and exit.
  -h, --help           Show help and exit.

Examples
  tushare-downloader list
  tushare-downloader fetch daily_basic -s 2026-09-01 -e 2026-09-10
  tushare-downloader update stock_basic

Use COMMAND --help for command options and examples.
```

底部实际帮助还给出稳定的 CLI 参考页 URL。主帮助仅保留三个例子；不重复 refresh、plain、配置等所有排列组合。

### refresh 子帮助示意

```text
Usage: tushare-downloader refresh [OPTIONS] API

Reconcile data when its last reconciliation is older than --max-age.
Missing or invalid records are always requested.
Use 0 to force re-fetching. Calendar filtering still applies.
Time-range APIs require both dates; snapshots reject dates.
Empty responses use EMPTY_RECHECK_AGE unless --max-age is 0.

Options
  -s, --start DATE      First date, inclusive (YYYY-MM-DD).
  -e, --end DATE        Last date, inclusive (YYYY-MM-DD).
  --max-age DURATION   Freshness threshold, e.g. 12h, 7d, or 0.
                       Config: MAX_AGE; default: 24h.
  --ignore-calendar    Bypass calendar filtering for this invocation.
  --dry-run            Preview the plan without downloading data.
  -h, --help           Show help and exit.

Examples
  tushare-downloader refresh daily_basic -s 2026-09-01 -e 2026-09-10 --max-age 7d
  tushare-downloader --plain refresh stock_basic --max-age 0
```

fetch 帮助给一个范围补取、一个快照示例；update 给 daily_basic 和 stock_basic 两个示例并解释两种更新策略。
clean 帮助先突出默认 preview 及实际执行需要的名称/UUID 双确认，再展示一个预览例子；不提供可误复制执行的真实数据库确认值。
参数错误只显示 Usage、一句具体错误和帮助入口，不自动倾倒整个帮助页。例如：

```text
Usage: tushare-downloader fetch [OPTIONS] API
Error: daily_basic requires both --start and --end.
Try 'tushare-downloader fetch --help'.
```

## 两个当前接口的适用规则

以下以当前实现核对，不新增业务能力。数据分类和请求形态分别描述，不能把“通常只增”误写为永远不修正。

| 命令 | daily_basic：只增型、按日请求 | stock_basic：可变型、完整快照 |
| --- | --- | --- |
| fetch | -s/-e 均必填；按日判断有效成功记录，需请求的块 upsert | 不接受日期；整个快照判断是否跳过，需请求则全部取得后 upsert |
| refresh | -s/-e 均必填；按有效核对时间和 max-age 判断；可靠非空响应可在当天范围标 stale | 不接受日期；按完整快照核对时间判断；必要子请求全部成功且全集非空才核对缺失键 |
| update | 不接受日期；从本地最新有效日减去 lookback-1，直到上海昨日；全窗口重拉/upsert，不做缺失键 stale 核对 | 不接受日期；每次重新拉取完整快照，成功后 upsert 和缺失键 stale 核对；不用 lookback 或 max-age |

daily_basic update 本地没有有效日期时应提示先 fetch；stock_basic update 不需要本地日期或已有行，也可从空表开始。
fetch 不对缺失键标 stale；upsert 仍可更新已有键的字段，并恢复重新出现的 stale 行。只增型 update 的历史修正入口仍为 refresh。
daily_basic 显式 fetch/refresh 可包含上海当天（暂定数据），不允许未来日期；update 默认止于昨日。
请求时间范围的两个端点均包含在内。只在日频 API 展示日历策略；stock_basic 的 --ignore-calendar 不产生行为变化。

refresh 的正常非空记录年龄取 `last_reconciled_at`，不是普通 fetch 的 `last_success_at`；从未核对、失败、不一致等情况必须请求。
非空有效核对记录 age <= max-age 才跳过；空记录使用 EMPTY_RECHECK_AGE，--max-age 0 强制请求优先。
报告展示实际决策原因，不把所有跳过概括为“24 小时内已下载”。

### update 帮助补充示意

```text
Usage: tushare-downloader update [OPTIONS] API

daily_basic: re-fetch from the latest local date minus the lookback
through yesterday (Asia/Shanghai). Fetch an initial range if empty.
stock_basic: reconcile the full snapshot; local data is optional.
Dates are not accepted. Freshness does not skip update requests.

Options
  --ignore-calendar  Bypass calendar filtering for time-range APIs.
  --dry-run          Preview without downloading data.
  -h, --help         Show help and exit.

Examples
  tushare-downloader update daily_basic
  tushare-downloader update stock_basic
```

### 报告因接口而异

daily_basic 计划展示用户范围（update 为自动范围）、最新本地有效日、实际请求窗口和适用策略。
例如 latest=2026-09-04、lookback=7、昨日=2026-09-13，则窗口是 2026-08-29..2026-09-13，不是简单“最近 7 天”。
stock_basic 计划只展示 Full snapshot、初始本地状态及是否执行缺失核对，不展示伪造日期、回看天数或交易日历。

stock_basic 是一个逻辑块，内部必要请求为 list_status=L/D/P/G/UN。
报告将逻辑块结果和子请求表分开：子请求只记录 Received rows，不能显示它独立 Committed。
任一必要请求失败、范围解析失败或键冲突，整个快照不合并，后续未发出的子请求写 Not attempted；已收到数据不代表已入库。
全部子请求成功但总结果为空时，标记 Empty / unverified，保留本地行，不标 stale。
单个状态为空而其余返回非空是有效快照的一部分，不能把它计为“一个空逻辑块”或必然待核实异常。
提交结果未知时，已提交行数 unknown；仅已确定未提交时写 0。

所有已确认写入输入行按互斥四类计数：Inserted + Updated + Unchanged + Reactivated。
Reactivated 行即使源字段同时改变，也只归入 Reactivated。四类占比均以已确认写入输入行总数为分母。
Newly stale 单独列出，其分母为成功执行缺失核对的非空范围在核对前的 active 行数。
fetch 和 daily_basic update 显示 Missing-key reconciliation: not applied；不要用“0% stale”暗示已经完成缺失核对。
快照报告可展示 active/stale 前后对照；只在取得可靠计数后填写，不为失败或提交未知情况推断结果。

## 单文件报告的生命周期

1. 日志建立后首先显示日志路径，保持已确认的启动行为。
2. 本地检查和日历准备完成后，先原子写入 `report.md`，包含计划、初始本地状态、范围明细和 `Final result: not recorded`，再开始数据请求。
3. 首次文件创建成功时显示 `Report: <path>`；长下载期间可打开它看计划，监看执行则使用日志。
4. 正常结束、可处理的失败或中断后，原子替换同一路径：结果在前，原计划保留在后。结束摘要再次显示该报告路径，方便立即打开。
5. 强制终止、机器断电或最终写报告失败时，已有文件保留；它不表示“仍在运行”，只表示该报告没有最终结果。实际执行可能已有提交，需查日志及数据库。

采用同目录临时文件写入完成后替换；不在每个块结束时重写完整报告，不追加拼接出半份 Markdown。
最终渲染复用不可变的初始计划，不重新推断或改写下载前事实。终端 quiet/verbose、REPORT_MAX_ITEMS 不裁剪报告。
报告 I/O 错误沿用原非零退出和已提交数据保留规则；不能为了报告失败回滚以前提交的块。
若计划阶段就失败，尽力生成简短失败报告，缺项写 not available；文件不存在时不输出假路径。
该文件不是恢复检查点，不增加 status/resume 功能。

## 最终报告的信息顺序

| 顺序 | 内容 | 密度规则 |
| --- | --- | --- |
| 1 | 标题、结果、命令、时间、版本、日志位置 | 用小型元数据表；命令和配置脱敏 |
| 2 | 执行摘要：块数、HTTP 尝试、写入分类 | 指标表，不逐个指标创建段落 |
| 3 | Needs attention：失败、未知、未尝试、空响应 | 非空时出现；先给可采取的行动 |
| 4 | Plan：初始范围、本地行数、请求/跳过/日历过滤、实际策略 | 保留原始计划；快照不显示回看参数 |
| 5 | Block details：计划决定和最终结果并列 | 每块一行，无截断；不复制原始业务数据 |

成功/失败比例分母、写入分类仍按[总体设计](overview.md)；计划跳过数不混入成功率。所有比例明确分母，零分母用破折号及说明。
Needs attention 可无损合并相邻且原因相同的范围，完整逐块表保留日期、块标识和实际结果。
HTTP attempts 包含重试；不把一个快照块等同一次 HTTP 请求。快照明细保留必要子请求的状态/筛选条件，只有整体核对成功才能给出已提交行数。
块表使用 Scope、Plan、Outcome、Attempts、Committed rows 五个紧凑列，错误原因集中在 Needs attention，用块标识关联。
超长范围报告流式写出，不在内存构造巨型字符串；不采用 <details> 折叠作为唯一访问方式，保证 GitHub、普通 Markdown 阅读器与打印可读。

## 状态与例外

- 零计划：只给 Nothing to download、跳过原因、本地状态和范围；不列写入全零表。日历筛掉全部数据块时仍需披露日历 HTTP 次数，不能写 No requests sent。
- dry-run：标记 Plan only，不生成伪造的执行结果；注明日历缓存刷新可能使真实计划变化。
- 提交未知：单独计数；该块写入行数为 unknown，而不是 0，不能混入确认写入统计。
- 日志轮转：报告列出实际生成的全部日志分片链接；启动日志入口的跨片自动跟随移入后续 backlog，不属于本版范围，不伪称 tail -f 会自动跟随其他文件。
- 最近日志、完整 traceback 和逐次重试保留在 JSONL；报告只收录必要诊断，不重复整份日志。
- 旧 before/after 文件原样保留，新执行只生成 report.md；文档和 demo 更新路径，不自动迁移用户历史文件。

## 完整报告样例

见 [日频部分失败报告](examples/report-example.md)、[快照更新报告](examples/report-snapshot-example.md) 与 [执行前报告](examples/report-plan-example.md)。样例代表结构，不是真实执行证据。
日期和数字用于验证表格及计数，不暗示该日一定有交易。

## 验收

- 主帮助、refresh、fetch/update、clean 和参数错误在 Rich/plain、40/80/120 列可读；示例参数通过解析检查。
- 六种展示组合的报告业务语义一致（不要求运行 ID、路径、时间戳和耗时相同）；帮助不依赖配置或外部服务。
- 开始数据请求前已有带初始计划的报告；最终报告保持同一计划内容，结果与块记录一致。
- 以故障注入验证临时文件写失败、替换失败、中断：已有报告不损坏，不产生假成功，不丢已确认提交。
- 覆盖零计划、dry-run、快照子请求失败、日历全过滤、提交未知和超长范围；所有块都能查到，无摘要截断。
- Markdown 表格中的管道、换行和来源文本须正确转义；所有示例和报告不泄露凭据。

日历策略补充：calendar 准备失败时停止并报告，不能自动改用 basic/off；--ignore-calendar 是用户主动绕过全部交易日过滤。缺失日历的 dry-run 标记计划不完整并退出 1。详见 [交易日过滤](request-planning.md)。
