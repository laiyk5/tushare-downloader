# CLI 体验设计

**设计版本：v0.2.0-draft.6**

## 命令契约

程序名称仍为 `tushare-downloader`。保留现有别名及参数位置；高频 -q/-v、一次性 --plain 保留。
长期 log-level/progress 偏好进入配置，不为翻译和排版增加选项。
stdout/stderr 优先服务人类阅读；JSONL 文件提供机器记录，不增加 --json、--no-color 等平行模式。

| 用户意图 | 命令示例 |
| --- | --- |
| 尽力补取范围 | `tushare-downloader fetch daily_basic -s 2026-09-01 -e 2026-09-10` |
| 重拉不够新的历史 | `tushare-downloader refresh daily_basic -s 2026-09-01 -e 2026-09-10 --max-age 24h` |
| 强制核对全部日期 | `tushare-downloader refresh daily_basic -s 2026-09-01 -e 2026-09-10 --max-age 0 --ignore-calendar` |
| 更新已有日频数据 | `tushare-downloader update daily_basic` |
| 对齐完整快照 | `tushare-downloader update stock_basic` |
| 预览 | 在下载命令后添加 `--dry-run` |

以上 --ignore-calendar 为拟新增选项；此页不是当前软件使用指南。
在三个下载命令上统一接受此选项；不适用接口无需额外报错，但不改变其行为。

## 帮助页

具体排版、Examples 及单文件报告规则见 [帮助页与完整报告](help-and-reports.md)。该页覆盖本页旧的 单文件 文件约定。

英文主帮助依次展示一句用途、Usage、按目的分组的命令、全局选项、简短示例和参考文档链接。
组为 Download（fetch/f、refresh、update/u）、Database（init-db/init、clean）、Inspect（list/ls）。
子命令帮助说明参数、默认值来源、限制及一至两个可运行示例；清理帮助保持确认要求醒目。
全局选项示例放在子命令之前，例如 `tushare-downloader --plain fetch ...`。
帮助展示静态默认规则，不加载 Token、不连接数据库、不请求日历或网络。
参数错误提供英文原因、相关 Usage 和 --help 入口；不打印完整环境变量或连接串。

## 视觉原型

[打开交互 Demo 与静态后备示意](cli-demo.md)。原型使用模拟数据，展示布局和模式差异，不替代本页行为规范。

## 两个独立维度

展示方式决定排版，信息量决定内容，六种组合均支持。默认是 Rich + normal。

| 维度 | 选择 | 控制方式 |
| --- | --- | --- |
| 展示方式 | rich / plain | 默认 Rich；PLAIN=true 或 --plain 使用纯文本 |
| 信息量 | quiet / normal / verbose | 默认 normal；-q 或 -v；二者互斥 |

`-v` 是单级展开，多次指定不建立额外详细等级。--plain 不等于 quiet，-v 也不强制打开动态进度。
PROGRESS=off 关闭动态进度和周期进度行，但保留对应信息量的事件日志。长期偏好保留在配置文件，不增加平行 CLI 开关。
本版新增配置 TERMINAL_LOG_LINES=5，允许 0..20；表示 Rich 中最多展示的最近日志条数，0 关闭最近日志区，不屏蔽警告错误。
不为终端展示增加额外日志级别配置；文件 LOG_LEVEL 与终端信息量分别负责持久化和展示。

## 启动、结束与输出流

稳定顺序为 Log location → Plan → Live activity → Result → Reports。计划和结果按信息量裁剪。
日志文件创建成功并写入启动事件后，立即打印并刷新 `Log: <path>`，早于本地数据库检查、日历准备和下载请求。
此行在所有信息量和展示模式下保留，便于 `tail -f <path>`；初始化失败则报错，不展示不存在的路径。
完整路径可换行但不省略；相对路径明确相对当前工作目录。结束不重复日志路径，只给出实际存在的报告文件位置。
未初始化日志的帮助、参数错误等不凭空生成日志路径或运行报告。

stdout：启动日志位置、计划、最终摘要、报告位置，以及 list/help/clean preview 的主要命令结果。
stderr：运行中事件、警告错误和活动区。交互界面用单个 renderer 串行绘制，禁止多个线程直接向终端写字。
阶段切换时暂停/结束 Live 再打印 stdout 面板，避免跨输出流导致交错。重定向后两个流各自有序，不承诺合并时逐字节全局排序。

## Rich 默认体验

普通支持终端控制的交互终端使用 Rich Panel、Table、Progress 和 Live，保留滚动历史，不进入全屏或 alternate screen，不接管键盘。
启动日志路径和计划是静态区域；运行中只有一个固定活动区域；结束后移除活动区域并打印最终结果，避免残留两份统计。
活动区包含进度摘要及最近日志：

```text
Log: /…/logs/<run>.jsonl

╭ daily_basic · update ─────────────────────────────────────╮
│ Range   2026-09-01 → 2026-09-10                            │
│ Plan    10 blocks                                         │
╰──────────────────────────────────────────────────────────╯
Downloading   ━━━━━━━━━━━━────────  6/10  60%
Elapsed 00:18   ETA ~00:12   HTTP 0.39 req/s
Written 30,000 rows   6 non-empty · 0 empty · 0 failed

Recent activity
14:51:14 INFO  Committed 2026-09-04: 5,000 rows
14:51:16 INFO  Committed 2026-09-05: 5,000 rows
14:51:18 INFO  Committed 2026-09-06: 5,000 rows
```

以上为布局假数据，不表示真实市场日期或执行结果。颜色使用青色表示活动、绿色表示成功、黄色表示警告、红色表示失败，标签同时表达含义。
接口名、结果和关键数字加粗；路径、单位和辅助说明弱化。不能只靠颜色区分状态。
80/120 列使用横向表格；40 列转为纵向字段，缩减日志区高度，优先显示当前阶段和错误。
日志条目可以换行，每条最多显示两行；截短处标注完整日志位置已在启动时给出。文件日志、最终故障详情和路径不因此截断。
极低终端高度无法容纳活动区时采用静态 Rich 事件输出，不靠整屏裁剪吞掉关键内容。

仅 stdout 与 stderr 均为 TTY 且终端支持控制序列时启用 Live。任一流重定向或 TERM=dumb 时，全局自动采用 plain，避免导出带边框/控制序列的文本。
保留现有 NO_COLOR → plain 规则。PLAIN=false 只是允许 Rich，不覆盖环境不支持、--plain 或 NO_COLOR 的降级选择。

## 最近日志的语义

这是同一运行事件流的人类摘要，不轮询 JSONL 文件，也不为界面反向读取日志。
使用有界队列保留最近 N 条符合终端信息量的事件；新事件进入、旧事件移出，保持时间顺序。日志窗口滚动不向终端历史无限追加 INFO 行。
显示本地时间 HH:MM:SS、级别、相关日期/块和简短描述；文件继续使用既有时间与结构化字段。
normal 展示阶段变化、块完成、重试、空响应、失败和准备错误，过滤内部 SQL、HTTP 参数及重复心跳。
verbose 在此基础上展示请求开始、尝试序号、限速/退避等待、跳过原因和块耗时；仍不展示原始数据行、Token、密码、认证头或完整连接串。
连续相同重试/警告可合并为 `×N`，保留最近时间和当前等待状态；不同块的故障不能误合并。文件事件仍逐次记录。

WARN/ERROR 到达时，经 renderer 输出一次静态诊断到 stderr 滚动历史，并可以在最近日志中保留同一事件的活动副本。
重绘不能反复追加诊断。最终失败摘要由执行结果生成，不依赖已滚出窗口的事件；日志队列丢弃旧条目不影响计数、报告或执行。
PROGRESS=off 时不使用 Live，仅追加符合信息量的阶段事件与块事件；不输出周期心跳。
TERMINAL_LOG_LINES=0 时保留正常进度，普通事件仅写文件；警告错误仍静态输出。

## plain 体验

纯文本是独立的人类阅读布局，不是去掉颜色但保留大表格。使用短标题、键值、空行和顺序事件行。
不含 ANSI、OSC 超链接、回车覆盖、边框、spinner 或进度条；不依赖对齐空格解析数据。
日志文件仍是机器消费入口，不承诺终端文字或列位置作为稳定协议。

```text
Log: /…/logs/<run>.jsonl

Plan: daily_basic | update
Range: 2026-09-01 to 2026-09-10
Blocks: 10 planned

14:51:00 INFO Preparing download
14:51:05 Progress: 2/10 blocks; elapsed 5s; ETA unavailable
14:51:10 WARN 2026-09-03: read timeout; retry 2/4 in 2s
14:51:15 Progress: 5/10 blocks; elapsed 15s; ETA ~15s

Result: completed
Blocks: 10 successful; 0 empty; 0 failed
Reports: reports/<run>/report.md
```

normal plain 以 PROGRESS_INTERVAL_SECONDS（现有默认 5 秒）周期追加进度，只在有活动时输出；阶段变化、WARN/ERROR 即时输出。
块完成信息已汇总在进度中，normal plain 不逐块刷行。verbose plain 逐事件追加块和尝试详情，但同样不打印每次 UI 刷新。
plain 不模拟最近 N 条回滚；TERMINAL_LOG_LINES 对 plain 不适用。PROGRESS=off 关闭周期行，保留阶段变化与警告；verbose 仍可看到块事件。
quiet 不输出周期行。最终摘要总会输出，无需额外重复一个最终 Progress 行。

## 信息量矩阵

| 信息 | quiet (-q) | normal | verbose (-v) |
| --- | --- | --- | --- |
| 启动日志路径 | 显示 | 显示 | 显示 |
| 下载前计划 | 隐藏；dry-run 除外 | 紧凑计划 | 计划与逐块理由，受摘要条数上限约束 |
| 活动进度、ETA、速率 | 隐藏 | 显示 | 显示 |
| 最近 INFO 活动 | 隐藏 | 最近 N 条 | 最近 N 条，包含请求/等待细节 |
| WARN/ERROR | 显示简短诊断 | 显示 | 显示更多脱敏上下文 |
| 成功结束 | 一行结果 | 结果及相关行统计 | 另加阶段耗时、请求/重试计数 |
| 部分失败/提交未知/中断 | 结果、必要计数及下一步 | 另列受影响范围 | 另列可用故障上下文 |
| 报告位置 | 显示 | 显示 | 显示 |
| Python traceback | 隐藏 | 隐藏，给出错误类别 | 非预期内部异常才显示，禁止捕获 locals |
| 文件日志/完整报告 | 不因 quiet 减少 | 按配置记录 | 不因 verbose 自动改文件 LOG_LEVEL |

LOG_LEVEL 控制持久化诊断详略；终端 -v 可消费已生成的诊断事件，即使文件配置不保存该级别。
基础运行事件、失败与最终结果仍遵守既有日志契约，不能让终端抑制条件参与其生成和持久化。
文件日志 I/O 故障继续按原失败语义处理；界面不是可靠存储的替代品。

quiet 不是静默协议：成功也给一行明确结果，用户无需从“没有输出”猜测是否运行完成。
help、list、clean preview、dry-run 的主要输出是用户主动请求的结果，-q 不隐藏；只减少附带诊断和装饰。
破坏性操作确认和配置错误不能被抑制，-q/-v 不改变确认条件、退出码和业务逻辑。

## 按结果选择布局

| 情况 | 主要表达 |
| --- | --- |
| 计划为零 | Nothing to download；本地行数、跳过理由、未请求云端；隐藏写入全零统计 |
| 普通成功 | Completed；块摘要、相关写入统计；没有非零计数的不相关附项可折叠 |
| 有空响应 | Completed with empty responses；突出需要核实的范围，不宣称数据完整 |
| 部分失败 | Completed with failures；已提交/失败范围、下一步；不能写全部回滚 |
| 提交状态未知 | Commit outcome unknown；优先展示受影响块，不能把它计入确定成功或失败写入 |
| 用户中断 | Interrupted；已确认提交、未尝试和未知状态；退出 130 |

避免把本地跳过写成 Up to date；未请求远端不能宣称已与云端对齐。
快照接口隐藏无关时间范围/回看参数；refresh 才突出新鲜度阈值；只增型 update 展示实际回看窗口。
正常终端摘要遵守 REPORT_MAX_ITEMS；失败、空响应可合并连续区间，明确省略数量并链接完整报告，不无界刷屏。
完整报告不受终端模式、信息量和条数上限裁剪。
成功比例包含成功空响应，以计划执行块数为分母；未尝试不能从分母剔除。零分母不显示无意义百分比。
写入行分类、重新激活与 stale 分母沿用原定义；仅展示相关指标不改变统计规则。

## 进度与实现建议

展示阶段、已完成/计划块、耗时、ETA、HTTP 尝试速率与确认写入速率，单位明确。
日历准备显示 Preparing calendar，无数据 ETA；数据执行沿用原样本阈值和窗口估计。
重试和提交停顿时突出阶段，ETA 暂不可用；空计划不创建 Live。
展示更新最多每秒 4 次，不能让每条事件触发终端刷新。仅终端线程消费状态快照和有界日志队列。
实现建议是在现有 reporting 内分离状态、信息量过滤和 Rich/plain renderer；先用简单函数/类，不引入通用 UI 框架。
所有 API 来源文本按普通文字渲染，禁用其 Rich markup 解释；移除终端控制字符，防止错误消息破坏布局或伪造提示。

## 验证

- 覆盖 rich/plain × quiet/normal/verbose 六种组合，并验证业务结果、退出码和完整报告相同。
- 无凭据、无数据库、禁网时主/子帮助可用；quiet 不隐藏 list/dry-run/clean preview 的主体。
- 日志路径先于数据库检查/日历/网络请求；长路径完整可复制；文件创建失败不显示假路径。
- 覆盖正常、零计划、空响应、部分失败、全失败、提交未知、中断、锁冲突和配置错误。
- 检查 40/80/120 列、低高度、TERM=dumb、NO_COLOR、单流重定向；plain 无 ANSI/OSC/回车控制。
- 用可控时钟检查 ETA、限速、重试和进度周期；不依赖真实等待。
- 高事件量下队列有界、最近 N 条正确、日志仍完整；重复重绘不重复追加 WARN/ERROR；结束后没有悬挂 Live。
- 验证 PROGRESS=off、TERMINAL_LOG_LINES=0、非法配置以及各信息量组合。
- 检查不可信 markup、控制字符、外部中文错误和脱敏；程序自有文本统一英文，源数据不翻译。
- 检查代表截图与 plain 文本；断言信息和计数，少量快照验证布局，不锁死所有空格。

日历策略补充：calendar 准备失败时停止并报告，不能自动改用 basic/off；--ignore-calendar 是用户主动绕过全部交易日过滤。缺失日历的 dry-run 标记计划不完整并退出 1。详见 [交易日过滤](request-planning.md)。
