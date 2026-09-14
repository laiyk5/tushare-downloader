# 总体设计

当前版本与状态见 [设计入口](index.md)。本文是 v0.2.0 的完整规范，不需要结合历史版本阅读。
目标软件 v0.2.0；当前软件基线为已验收 v0.1.0。设计不表示新功能已实现。
Python 3.12、PostgreSQL 18、WSL/Linux；shell 示例默认 Bash，软件交互英文、设计中文。

## 1. 目标与范围 {#section-1}

一个 API 一张表，一个 PostgreSQL 数据库容纳全部数据。用户在当前 shell 启动下载器，查看计划、当前进度与单文件执行报告；失败后重新执行命令即可。

程序负责：本地范围自检、请求计划、限速、分块、有限重试、去重、批次写入、更新与 stale 标记、结果报告。没有后台服务、持久执行计划、任务列表、执行历史查询命令或断点恢复协议。不提供 resume、status、watch、sync configure；不保存 run/batch 状态机或成功游标。

本版增加的本地检查服务于“下一步需要请求哪里”。它能够报告未查、失败、空响应和已取得数据的范围，不承诺源端业务完整性。业务清洗、财务口径选择、复权、跨表关联及指标验证属于后续处理。

## 2. 数据分类 {#section-2}

推荐将两种数据称为 **只增型（append-only）** 和 **可变型（mutable）**。“增量”描述一次请求或更新方式，不能准确表示数据本身是否允许修改；可变型如果源端提供变更接口，同样可以增量获取。本文“只增型”表示通常只增加新键，日常按不改不删处理，但允许源端低频校正已有值或撤回记录；它是默认更新策略的假设，不是绝对不可变的保证。append-only 在本文仅作这个策略标签，不能按严格追加日志的含义理解。

查询形态是另一个独立属性：**时间范围型（time-range）** 能按声明的日期范围查询；**当前快照型（snapshot）** 只能查询当前集合。日期字段的存在不代表接口支持历史范围，例如股票上市日期不能当作快照的查询游标。

ApiSpec 用两个普通枚举字段表示：change_kind=append-only|mutable，query_kind=time-range|snapshot，不增加策略框架。数据类型由接口定义负责，list/帮助/下载计划摘要均显示；用户不必每次在 CLI 选择。分类描述日常更新策略；偶发源端错误或历史纠正不构成改分为可变型的理由。

只增型快照用于通常保留已有记录的累计集合；滚动窗口导致旧记录常规退出时属于可变型。四种组合的命令行为统一见第 3 章。

## 3. 用户意图与命令 {#section-3}

本节是命令请求范围、跳过条件和写入意图的唯一规范来源。块编号和选块过程交给[请求规划算法](request-planning.md)，终端呈现交给[交互设计](cli-experience.md)。

| 命令 / 数据类型 | 请求需求 | 跳过条件 | 返回行写入 | 未返回旧键 |
| --- | --- | --- | --- | --- |
| fetch | 用户指定时间范围；快照为当前集合 | 已有有效成功记录可跳过；失败/覆盖不足重查，空响应按复查间隔 | upsert，返回的 stale 行恢复 active | 保留 |
| refresh | 用户指定范围；快照省略日期 | 完整核对年龄 ≤ max-age 可跳过；0 强制；空响应按下述例外 | upsert，恢复 active | 按第 5 章规则标 stale |
| update：只增型时间数据 | 本地最新 active 日期回看 LOOKBACK_DAYS 至接口终点 | 需求内不按存在性、新鲜度或空响应间隔跳过 | upsert，允许窗口内修正 | 保留 |
| update：只增型快照 | 当前全集 | 不跳过 | upsert，允许修正 | 保留 |
| update：可变型（两种查询形态） | 源端完整集合；时间仅是拆请求的方式 | 不跳过 | 整体 upsert，恢复 active | 按第 5 章规则标 stale |

本地判断产生的候选块再按 [交易日过滤规则](request-planning.md#trading-day-filter) 处理。默认 basic；calendar 失败不自动降级；--ignore-calendar 主动绕过。

表中的需求会映射为固定块，允许夹带邻近日期；计划摘要说明用户范围与实际请求范围。源字段更新、NULL 和 stale 的具体写入规则只在第 5 章定义。

list 显示支持接口、数据分类和请求能力；init-db 初始化受管理对象；clean 预览或显式清空 API 数据。初始化和清理的权限、身份校验见第 10 章。

### 3.1 高频选项与缩写 {#section-3-1}

仅安装 tushare-downloader 一个程序入口，不内置短命令名；用户可自行配置 shell alias。高频子命令保留固定缩写 fetch=f、update=u、list=ls、init-db=init；低频 refresh 和 clean 使用全名。禁止模糊前缀匹配。

| 位置 | 选项 |
| --- | --- |
| 全局 | -h/--help、--version、-q/--quiet、-v/--verbose（单级展开）、--plain、-c/--env-file PATH |
| fetch / refresh | API 位置参数；-s/--start、-e/--end；--dry-run；--ignore-calendar |
| refresh | --max-age DURATION：本次新鲜度要求，覆盖配置；0 表示本次强制核对 |
| update | API 位置参数；--dry-run；日期边界和回看规则来自接口与配置，不提供局部范围选项；--ignore-calendar |
| clean | API 位置参数；--apply、--confirm-database NAME、--confirm-database-id UUID |

全局选项放在命令之前。策略与清理确认保持全名。fetch 不提供 max-age：主动刷新用 refresh。接口若为快照，无日期参数；时间序列 fetch/refresh 必须同时指定起止且包含端点。

```bash
# 补齐指定日期区间；失败后可原样再执行
tushare-downloader f daily_basic -s 2026-01-01 -e 2026-03-31

# 核对修正；24 小时内已核对的分段跳过
tushare-downloader refresh daily_basic -s 2026-01-01 -e 2026-03-31 --max-age 24h

# 更新本地已有范围，并追赶默认终点
tushare-downloader u daily_basic

# 更新当前快照；不需要也不接受日期范围
tushare-downloader u stock_basic

# 强制重新核对全部快照
tushare-downloader refresh stock_basic --max-age 0

# 只做本地自检和计划，不调用 Tushare 或修改数据库
tushare-downloader --plain f daily_basic -s 2026-01-01 -e 2026-03-31 --dry-run
```

### 3.2 默认值、例外与例子 {#section-3-2}

- refresh 默认 MAX_AGE=24h，判断时间在本次计划开始固定；只使用覆盖本次实际范围、spec 兼容且最近尝试未失败的 last_reconciled_at。未到复查时间的空响应另列“暂缓复查”，--max-age 0 仍强制请求。新鲜度不是 _updated_at。
- 只增型时间 update 的 LOOKBACK_DAYS 默认 7，必须为正，包含本地最新日；不是从系统当前日期向前回看。例：本地最新 3 月 10 日、lookback=3、终点 3 月 15 日，需求为 3 月 8–15 日。空库或无 active 日期时先 fetch 初始化。本地最新日期若晚于默认终点，先截至终点再回看，避免当天暂定数据使窗口越界。
- 时间范围 fetch/refresh 必须成对提供起止且包含端点；快照均拒绝日期参数。update 不接受日期或 max-age。当前快照不能重建从未下载过的历史快照，空库可以直接 update。
- update 窗口之外的历史缺口用 fetch，历史校正用 refresh。重发 update 会按当时本地最新日重新计算窗口；旧失败若已在窗口外，按报告 fetch 指定范围。
- 可变型的源端完整范围须由 ApiSpec 声明，不能用本地最早日期代替。范围无法枚举时拒绝全量 update，提示指定范围 refresh；待核验接口能力集中列于第 16 章。

只增型的低频校正使用现有 refresh，不增加专用快捷命令；校正不会改变后续 update 的数据分类。

## 4. 执行流程与成功判定 {#section-4}

配置/参数校验 → 建立日志并显示路径 → 本地自检 → 块需求与交易日过滤 → 原子写入 report.md 的初始计划 → 顺序请求及写入 → 原子更新完整报告。--dry-run 复用自检与计划，只不请求远端、不修改数据库。可执行计划不作为恢复状态持久化；report.md 保存其可读记录。

自检产生事实，第 3 章决定是否需要请求，[算法文档](request-planning.md)负责计算块边界，存储层负责第 5–6 章的提交规则。展示和日志不反向决定数据行为。

### 4.1 本地检查事实 {#section-4-1}

| 分类 | 判定 | 报告含义 |
| --- | --- | --- |
| 已取得非空分段 | 当前记录与兼容的成功检查记录一致，最近尝试未失败 | 可作为已有范围事实 |
| 尚未检查 | 无成功检查记录；即使已有一些行也不能证明整段完整 | 仍需取得 |
| 曾失败 | 最近尝试失败或结果不可用 | 最近尝试未成功 |
| 成功空响应 | 源端返回空，但原因不明 | 空响应，原因待核实 |
| 本地记录不一致 | 行数/技术时间等基本检查与成功记录不符，或 spec 不匹配 | 旧成功依据不可用 |
| 暂未到发布时间 | 接口规则认为尚未稳定发布 | 明确列出；用户显式指定时可请求，但不作为永久历史跳过依据 |

raw 检查包括目标范围内 active/stale 行数、日期分布，以及与分段记录的基本一致性。只看 MIN/MAX 或“当天有一行”不够；也不逐次对全表计算哈希。数据库由本下载器写入，外部直接修改 raw/meta 不受支持；无法靠行数检查检测所有外部同数修改。

尚未稳定发布时取得的结果到发布时间之后必须再查，不能因当前已有成功记录就永久跳过；last_success_at 与 ApiSpec 发布时间规则共同决定这一点。

“已取得”只表示某次完整协议响应已成功处理，不意味着股票、交易日或业务内容绝对齐全；不因返回量达到上限否定成功。报告分开列出本地无行、成功空响应和未检查，不伪造完整率。固定地址按自然日计算；是否过滤周末或休市日由交易日过滤策略决定，过滤不生成成功记录。

### 4.2 成功记录与数据完整性的边界 {#section-4-2}

API 返回成功且响应可解析、声明的必要分页/枚举已执行、数据事务已提交，就记录这次请求成功。成功标记代表按既定请求协议取得并保存了响应，不是业务完整性证明。HTTP 错误或 API 非成功业务码（包括限流、额度、参数及源端明确报告的数量限制错误）始终按失败分类处理，按既有规则重试或报告失败；HTTP 200 不能覆盖非成功业务码。错误响应即使附带数据也不按成功入库、不刷新成功记录、不作为 stale 依据。

仅在 HTTP 与 API 业务码均表示成功时，不额外把“返回行数等于上限”判断成失败，不为此自动二分日期、递归拆请求或猜测缺失行数。已明确的分页协议仍须执行；HTTP/业务错误、网络响应损坏和类型错误仍正常报错。已知行数上限作为接口参数与性能信息保留，不作为完整性判定器。

源端无报错漏数可能无法识别；fetch 成功跳过不会自动修复这种遗漏。只增型 update 回看可重新取得近期数据，历史范围用 refresh，用户后续验证也可发现问题。这些机制提供重新取得数据的入口，不承诺必然发现和修复所有历史遗漏。

## 5. 数据存储与写入 {#section-5}

数据均按 API 明确的唯一键存储当前版本。不同时提供 append/keyed 两种存储模式，也不保存每次抓取的旧值历史。业务字段变化而唯一键也变化时按旧键 stale、新键插入处理；下游引用保留旧键但需自行决定如何关联新键。新增 API 没有可靠唯一键时，先补充该 API 的具体设计，不猜测键。

除 raw.<api> 外，只保留两张内部表：

| 表 | 目的与字段 |
| --- | --- |
| meta.schema_info | 单行数据库身份 database_id、application_id、schema_version，以及已初始化 API 的 spec 版本映射 |
| meta.slices | 每 API/spec、每固定块（或 snapshot）一行：block_id、requested_start/requested_end、last_attempt_at/outcome、last_success_at、last_result_kind、last_row_count、last_reconciled_at、local_active_count、local_stale_count、spec_version |

meta.slices 是本地数据的检查记录，不是一次执行的任务表：不含执行 ID、待办队列、running 状态、恢复指针或历史尝试列表。同一分段只更新最新检查事实；完整尝试历史在文件日志。失败仅更新最近尝试结果，保留上次成功事实，不刷新成功时间。

local_active_count/local_stale_count 保存提交后的本地行数，不能把返回行数 last_row_count 当成保留 stale 或旧行后的表行数。检查只在相同规范分段内比较这些统计。

last_success_at 使用成功请求开始时的 UTC 时间，保守计算数据年龄；last_reconciled_at 仅在成功执行完整对齐（含允许的缺失键处理）后更新。跳过请求、失败、显式分页未完成不能延长新鲜度。时间在未来或 spec 不匹配的记录视为不可信。

raw.<api> 使用源字段和以下技术列：

- _is_stale：是否已在完整核对中观察到缺失，默认 false。
- _stale_at：第一次由 active 转为 stale 的时间；重新出现后清空。
- _last_seen_at：该行最近实际返回并成功提交的观察时间。
- _updated_at：源字段值或 stale 状态最近改变的时间。

技术列不是业务字段；旧行被标 stale 时保留唯一键和所有源字段，不物理删除，避免破坏下游引用。下游自行选择是否过滤 _is_stale=false。所有行的业务唯一约束覆盖 stale 行，重新出现时更新原行。

### 5.1 对齐规则 {#section-5-1}

只有一个逻辑分段的所有请求成功、结构与终止条件通过，才进入该分段的数据事务：

1. 将完整响应装入临时 staging 表，按声明唯一键检查重复。
2. 新键插入；源字段不同则更新；相同值计未变。SQL NULL 是返回值，可以覆盖旧值。
3. 返回的 stale 行恢复 active；恢复计数单列，避免混入源字段更新。
4. 对启用了可靠缺失判定的 refresh/mutable update，在该分段范围内将未返回的 active 键标 stale。
5. 写入分段检查记录，与数据同事务提交。

本章“完整”只指声明核对范围的请求流程成功执行，不额外证明源端无漏数；协议成功判定见 4.2。

stale 仅表示“最近完整核对时未返回”，不声称知道源端删除原因。不同 API、日期或筛选范围外的行绝不能受到影响。已经 stale 且仍未返回的行不重复计为新增 stale。

### 5.2 不允许作为缺失证据的情况 {#section-5-2}

请求失败、显式分页未结束、结构错误、权限错误或未请求全部声明核对范围时，不执行缺失键标记。HTTP 与业务码均成功时，返回行数等于上限本身不额外触发失败或禁用 stale；stale 依据本次成功请求的集合，仅表示观察到未返回。

空响应必须由接口语义判定：若该 API 没有可靠的“空集合即完整空快照”契约，保留旧数据，标记 empty_unverified 并提示复查，不刷新 last_reconciled_at。当前两个接口均采用这一保守空响应规则；不能一次空响应就把全表或全日都标 stale。以后明确验证空集合语义的 API 才可据此标记整个范围，且测试必须覆盖。

数据提供方可能返回无显式错误的部分数据，下载器不能完全识别。ApiSpec 按明确的核对范围和分页规则启用 stale，不设计额外的业务完整性探测；首次真实冒烟应核实该依据。多请求也不保证源端原子快照；同一键出现冲突值时整段报错，不按返回顺序任取一条。

### 5.3 三种去重 {#section-5-3}

- 本次调用内：同一规范分段只计划一次；重试是该分段的新尝试，不增加业务分段数。
- 响应内：同键且全部源字段相同可折叠并报告数量；同键不同值整段失败，不任意保留首行/末行。
- 数据库内：以业务唯一键处理插入/更新。同值不改源字段或 _updated_at，但更新 _last_seen_at；这仍有数据库写入开销，benchmark 必须计入。

跨调用省流依赖分段检查记录，不依赖文件日志，也不引入请求缓存、TTL 引用链或恢复管理。

fetch 更新 last_success_at 而不产生新的 last_reconciled_at；只有执行了允许的范围对齐才能刷新后者。成功时间与实际范围随数据提交，不能用文件日志推断成功。

## 6. 失败、重试与事务 {#section-6}

### 6.1 尽力完成 {#section-6-1}

失败后的继续和提交行为按下表执行，退出码见 8.2：

| 故障位置 | 是否继续请求 | 目标数据与报告 |
| --- | --- | --- |
| 独立块请求重试耗尽 | 继续其他独立块 | 已提交块保留；失败块不写，结论非成功 |
| 可变型全量中的必要请求失败 | 停止本次快照的后续子请求 | 全量不合并目标表、不标 stale，见 6.3 |
| 全局权限/额度/数据库故障 | 停止 | 已提交结果保留，余下范围列为未尝试 |
| Ctrl+C | 停止 | 回滚未提交事务，尽力报告 |
| COMMIT 确认丢失 | 停止 | 标记提交未知，不断言回滚，不盲目重放 |

认证无效、接口无权限、已确认日额度耗尽、数据库不可用、表结构不兼容等全局性错误立即停止，报告已成功、已失败以及因停止而未尝试的范围，不将未尝试伪装为失败请求。持续网络故障可按配置连续失败阈值停止（默认 10 个分段）；阈值 0 表示禁用，独立于单请求重试次数。

硬退出不保证报告完结；日志文件可以是部分记录。再次执行是一次新的调用，重新自检和制定范围，不恢复旧执行。

### 6.2 有限重试 {#section-6-2}

| 情况 | 行为 |
| --- | --- |
| 连接/读取超时、可重试网络错误、HTTP 429/5xx | 按分段请求有限重试，所有尝试参与限速 |
| 参数/权限错误、未知业务错误、协议/类型错误 | 不盲目重试；分段错误或全局停止按影响范围判定 |
| Retry-After 超过允许等待预算 | 报告暂不可重试，不提前请求或等待一天 |
| 数据库 SQL/约束错误 | 回滚当前段，若明确是段内数据问题则继续，否则停止 |

MAX_ATTEMPTS=4 表示首次加 3 次重试；指数退避加随机抖动，遵守有限等待。requests 底层重试关闭，只有一层重试控制。HTTP 状态与 Tushare 业务码分开解析，不能靠含糊字符串把所有异常当限流。

连接超时、读取超时不等于整个命令总期限。响应体设字节上限以控制资源；超限明确报资源错误，与源端行数上限不同。API 声明分页时按协议读取；仅当 HTTP 与业务码均成功时，不因返回行数触顶自动拆块或报 possible_truncation。

### 6.3 事务与同库写入 {#section-6-3}

stock_basic 的 L/D/P/G/UN 响应组成一个逻辑快照，先在有界内存缓冲中完成所有必要请求和去重，再以 COPY/staging 在一个短事务内合并目标表、标 stale 并提交检查记录。HTTP 期间不持有目标数据事务。任一必要请求失败或冲突时停止该快照后续请求，整体不合并；后续子请求记为未尝试。单个状态为空不等于整体为空，整体空响应按 5.2 保留旧数据。预算超限明确失败，不先写半个快照。

每个完整逻辑核对范围一个事务。通常是一个固定时间块；可变型全表 update 的范围是整张 API 表，因此该命令的数据合并与 stale 必须一次提交。只增型及指定日期范围命令按块分批入库；若单段包含分页，全部分页先验证，再整体提交。使用有界缓冲，超过该 API 的内存/响应上限报错或由专用分块实现处理，不先写半段再做 stale。

同一数据库仅允许一个本程序写实例，以 session advisory lock 快速拒绝第二个写入者。HTTP 期间不打开数据库事务；同一连接持有实例锁、用短事务提交。此锁仅防重复实例和写入竞争，不形成任务管理功能。

COMMIT 确认丢失时停止当前调用，明确显示该段“提交结果未知”，不要误报回滚或盲目重放。新调用从 raw 与分段记录的原子结果重新判断；upsert 和键约束保证可安全重新请求。没有额外的提交恢复状态机。提交后日志写失败不会撤销数据，也不能因此重抓。

## 7. 配置与日志 {#section-7}

配置完整模板、默认值和整理规则见 [配置设计](configuration.md)。优先级为显式 CLI > 环境变量 > 指定 dotenv > 默认值；默认 cwd/.env，不向父目录搜索，显式不存在文件报错。dotenv 不作为 shell 脚本执行，不插值；相对路径基于 cwd。
测试与 benchmark 只接受独立的环境连接参数，不加载或回落正式数据库配置。凭据不进入命令、报告、日志和站点。

日志使用标准库 logging 和 JSONL，每次调用独立标识仅关联文件，不构成任务 ID 或恢复协议。
按 10 MiB 轮转，本次所有分片保留；历史清理由用户维护。报告列出所有实际分片，启动文件路径不保证 tail 自动跟随其他分片，便捷跨片监看入口移入后续 backlog，不属于 v0.2.0 范围，不能宣称已支持。
事件包括 invocation_started、coverage_before、slice_result、coverage_after、invocation_finished，以及请求尝试、重试、计数、错误和耗时。关键结果保留，LOG_LEVEL 控制诊断细节；终端模式不裁剪文件记录。
输出目录在下载前验证；日志 I/O 错误停止后续数据请求，尽力输出失败报告并非零退出，已提交数据保留。日志不与数据同事务，不能用日志替代数据库成功事实。
单文件 report.md 生命周期见 [帮助与报告](help-and-reports.md)，终端最近日志及输出流见 [CLI 体验](cli-experience.md)。

## 8. 统计与退出码 {#section-8}

### 8.1 统计口径 {#section-8-2}

可变型全表 update 在提交统计中视为一个逻辑核对范围，网络分页成功数另列；暂存成功不能计作已入库成功。只有全表合并提交后才统计行结果，失败时说明目标表保留旧值。日期型全量成功后各日检查记录与目标数据同事务更新，不能只更新总范围而留下旧的日记录。

设计划请求段数 P，成功非空 S，成功空 E，失败 F，未尝试 U，提交未知 Q，则 P=S+E+F+U+Q。本地跳过 K、周末过滤 W 和日历过滤 H 单列，成功规划时 T=K+W+H+P；日历准备失败时计划尚未确定。它们不能作为本次远端请求成功。重试次数是 HTTP 尝试，不增加 P。

- 执行成功比例：(S+E)/P；空响应同时单列为待核实。P=0 显示“不适用”，不显示 100%。
- 失败比例 F/P、未尝试 U/P、提交未知 Q/P 分别展示。
- 不计算“云端数据完整率”；本地边界和成功空响应不是完整性证明。
- 成功提交响应去重后的唯一行数 R，拆为新增 I、active 源字段更新 C、active 未变 N、重新激活 V，R=I+C+N+V。恢复行即便值也变化仍只计 V，细节可单独记录。
- I/C/N/V 的百分比分母为 R。新标 stale D 不属于返回行，单列 D/A，A 为已执行可靠缺失核对范围内、事务开始前的 active 行数。分母 0 显示“不适用”。
- 只统计已确认提交效果；数据库提交未知时不计作已确认新增/更新。

### 8.2 进度事实与退出码 {#section-8-3}

进度和吞吐以执行器提供的事实为准，已确认入库与网络取得/暂存分开计数。失败可以计为已处理，但不能计为成功；计划处理达到 100% 不等于命令成功。展示不得改变请求、写入或错误处理。ETA 是可缺失的估计，不是业务状态。

进度条、采样与刷新频率、ETA 展示及降级见[CLI 交互与输出设计](cli-experience.md)。

退出码：0 无执行失败（空响应可作为待核实警告）；1 部分/全部失败、未尝试或提交未知；2 参数/配置错误；3 同库实例锁冲突；130 用户中断。0 不等于业务数据完整。

## 9. API 与代码结构 {#section-9}

### 9.1 API 显式定义 {#section-9-1}

ApiSpec 使用普通 dataclass/字典，声明：API 名、固定字段/类型/唯一键、block_origin/block_days、块编号和边界函数、规范请求参数、协议终止规则、行数上限、限速、change_kind、query_kind、完整源范围枚举/发布时间规则、缺失判定能力、空响应语义及 spec 版本。没有通用插件系统。

当前接口定义如下；v0.1.0 的实际验证记录保存在 [验收记录](../development/acceptance.md)，新增规则仍需 v0.2.0 验收。

| API | 业务唯一键 | change_kind / query_kind | 请求定义 |
| --- | --- | --- | --- |
| daily_basic | ts_code, trade_date | append-only / time-range | 1 天一块；update 默认到 Asia/Shanghai 昨日 |
| stock_basic | ts_code | mutable / snapshot | list_status=L/D/P/G/UN；五个必要子请求组成一个逻辑快照 |

接口参数与候选实现依据：[daily_basic](https://tushare.pro/document/2?doc_id=32)、[stock_basic](https://tushare.pro/document/2?doc_id=25)。执行语义统一引用第 3 章，不按接口再重复定义。

### 9.2 HTTP 与解析 {#section-9-2}

使用 requests.Session 直接封装官方 Pro HTTPS 协议，保留 HTTP 状态和业务码。不依赖 pandas/ORM，不访问 SDK 私有字段；默认 https://api.tushare.pro，不自动降级 HTTP。[HTTP 协议](https://tushare.pro/document/1?doc_id=130)

字段按名字映射，允许顺序变化；缺字段、重复字段、行宽不符、非法日期或不可表示类型明确失败。不静默丢行或截断字符串。代码文本保留前导零。numeric 字段用 Decimal 路径，不能先转 float 再声称精度保真。源端 null 映射 SQL NULL，空字符串按具体字段声明处理。

### 9.3 最小代码划分 {#section-9-3}

```text
src/tushare_downloader/
  cli.py          # 命令解析，调用下载流程
  config.py       # 读取并校验配置
  apis/           # ApiSpec 注册及首版两个接口（保留已有包结构）
  planning.py     # 固定块与本地记录选择
  calendar.py     # 周末/可选日历分类与缓存
  client.py       # HTTP、限速、重试、响应解析
  download.py     # 自检、计划、循环执行；分段失败继续
  storage.py      # SQL、staging、upsert、stale、分段检查记录
  reporting.py    # 单文件报告、计数、Rich/plain、结构化日志
tests/
  unit/
  integration/
benchmarks/
```

先保持这些模块，需要时再拆文件。业务算法可用纯函数，时钟/sleep/HTTP 可注入测试；不引入服务容器或抽象基类体系。主流程为：配置/日志 → 本地自检与过滤 → 初始报告 → 顺序请求及事务 → 完整报告。计划在内存生成，不持久化待办清单。

## 10. 数据库初始化、维护与清理 {#section-10}

数据库名：正式 tushare，测试 tushare_test，性能 tushare_bench，恢复演练 tushare_restore_check。raw 为 API 数据，meta 为两张检查元数据表，analysis 留给下游用户。表名小写 snake_case，源字段不能与保留技术字段冲突。

管理员提前创建数据库和非超级用户 tushare_writer；下游 tushare_reader 只获 CONNECT、raw USAGE/SELECT。analysis 的权限单独授予。测试和 benchmark 使用独立账号及数据库，不允许配置缺失时回落正式库。

init-db 在一个事务内创建受管理对象和标识，重复调用校验已有列、类型、唯一约束和 spec；不兼容明确报错，不自动 ALTER/DROP 或接管外部同名表。新增接口允许原子补建相应表。标识符由注册表提供并用 psycopg.sql.Identifier，数据用参数绑定/COPY。

保持 PostgreSQL autovacuum；大量导入后可执行 ANALYZE，正常维护使用 VACUUM (ANALYZE)，不自动执行 VACUUM FULL。常规统计不当作长期业务覆盖缓存。

clean API 默认展示数据库身份、目标 API、拟删除 active/stale 行数和检查记录数。--apply 必须匹配库名及 database_id；一个事务内删除对应 raw 和 meta.slices 数据。下游外键阻止删除时整体失败，不级联删除下游对象。日常 stale 不物理删除，物理清理始终是用户显式操作。

备份使用 pg_dump 自定义格式备份整库，raw 与 meta 同一快照；恢复到新库演练，验证唯一键、stale、检查记录、样本 SQL 和只读权限。角色/权限需另行重建或授权，不能通过复制运行中的 PostgreSQL 数据文件替代备份。无自动迁移/调度服务。

## 11. 项目配置 {#section-11}

```bash
uv init --package --python 3.12 tushare-downloader
cd tushare-downloader
uv add requests "psycopg[binary]" python-dotenv click tzdata rich
uv add --dev pytest pytest-cov ruff pre-commit
uv add --group docs zensical
uv sync --locked
```

提交 pyproject.toml、uv.lock、.python-version；依赖具体版本以 lock 为准。保留 uv 生成的 build-system；唯一 console script 为 tushare-downloader，指向 tushare_downloader.cli:main。测试不依赖真实 Token。

Ruff 同时负责检查和格式化；pytest-cov 使用 branch coverage 找遗漏，不为首版虚构覆盖率门槛。pre-commit 安装 Ruff 检查/格式化 hook，hook 版本显式固定，不在每次提交跑真实 API 或数据库重测试。CI 固定 uv/Python 版本，构建 wheel 后验证安装入口。

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit --cov=tushare_downloader --cov-branch
uv run pytest tests/integration
uv run pre-commit install
uv run pre-commit run --all-files
uv build
```

.env、.venv、日志、报告、coverage 产物、site/ 和 benchmark 结果目录放 .gitignore；仅提交脱敏配置示例和人工选定基准报告。

## 12. 测试与验收 {#section-12}

测试采用等价类划分与边界值分析；代表用例不能证明全部输入正确。单元测试使用假 HTTP、假单调时钟和 sleep；集成测试使用独立真实 PostgreSQL，不用 SQLite 模拟事务/COPY。

| 验证层 | 唯一规则来源 | 必测组合或故障点 |
| --- | --- | --- |
| 命令与数据分类 | 第 2–3 章 | 三命令 × 当前两个注册 API；空库、日期参数非法、阈值等号及强制刷新；未来类型组合不要求新增实现 |
| 本地检查 | 第 4 章 | 无记录但有行、旧 spec、最近失败、空响应、本地记录不一致 |
| 请求规划 | [算法测试矩阵](request-planning.md#section-5) | 日期等价类/边界以及块记录与命令的组合 |
| 响应与重试 | 第 4.2、6.2、9.2 节 | HTTP 200 + 非成功业务码；成功且行数触顶；超时/限流/显式分页失败 |
| 存储与事务 | 第 5–6 章 | staging 后失败、stale 重现、跨范围保护、全量部分失败、确认丢失后重发、双实例竞争 |
| 统计与输出 | 第 8 章、[交互测试](cli-experience.md) | 计数守恒、零分母、长报告完整性、日志失败、提交与展示时序 |
| 运维与配置 | 第 7、10–11 章 | 配置不回落正式库、同名外部对象、外键阻止清理、wheel 安装入口 |

每个测试按上表追溯规范，不在测试章节重新规定命令含义。实现验收要求这些检查通过并记录结果；真实接口验证在独立环境记录协议、字段、错误分类和日历策略证据，验收平台为 WSL/Linux Python，覆盖 WSL 连接 Windows PostgreSQL；不要求 Windows 原生 Python。Excel 仅为可选 Demo。真实 Token 不进入自动测试，缺失集成数据库配置必须明确失败而非偷偷使用正式库。

## 13. benchmark {#section-13}

分别测量假 API（执行/解析开销）、固定数据真实 PostgreSQL（入库开销）、少量真实 API（网络/限速），不混为一个下载速度数字。

场景包括：首次补齐、全部可跳过、仅中间失败需补、部分过期刷新、全量刷新、append-only 追增、mutable 删除/重现、空响应、重复键和长报告。比较不同固定块大小的 HTTP 尝试次数、夹带行数、耗时与限速等待；不只比较去重后行数。每种场景明确数据规模、分段数、新鲜度、API 限速、DB/硬件/依赖版本。

记录墙钟 total、HTTP 尝试与成功次数、限速/重试等待、解析、入库、报告写出时间、峰值内存、响应字节。行速率区分输入行、业务新增/更新、stale/恢复以及 _last_seen_at 技术更新，不把同值核对称为零写入，不把跳过数称为下载吞吐。

每个固定场景至少 5 次，保留全部结果，报告中位数与波动；真实 API 结果不设固定 CI 门槛。额外对比 Rich/plain、PROGRESS=off、DEBUG 和大报告开销。先通过正确性测试再优化速度，不以 benchmark 关闭默认日志却不说明。

## 14. 文档与部署 {#section-14}

| 读者 | 入口及内容 | 不应出现的内容 |
| --- | --- | --- |
| 使用者 | README、guide、reference：安装、命令、配置、限制、故障处理 | 内部提醒、未完成验收清单 |
| 运维人员 | operations：初始化、权限、备份恢复、维护清理 | 实现过程流水账 |
| 贡献者 | development：环境、测试、benchmark、贡献流程、backlog | 冒充已交付功能的计划 |
| 设计评审者 | design：规范、理由、边界、待决项 | 运行状态的唯一记录 |

本版拟将面向使用者及运维的文档统一为英文，与 CLI 术语一致；设计文档保持中文。
历史验收与设计记录保持原语言和内容，贡献者文档不强制全量翻译。
维护提醒迁入 development，必要的用户限制保留。既有 URL 保留，移动页面保留导航页或重定向。
每条规则只有一处详细定义，其他页面链接引用；帮助例子和 reference 以实际命令验证。

继续使用 Zensical 和 GitHub Pages。PR 只构建；main 构建通过后部署同一产物；`docs-build` 保持必需检查。
新增设计页面加入导航和 CI 页面存在性检查。文档改动不触发生产数据访问。
Excel Power Query 只作为使用示例，不作为版本验收门槛。


文档 CI/CD 契约：

- PR：只读权限，安装锁定环境，严格构建并检查首页/导航/资源；保存 site artifact，禁止部署。稳定检查名 docs-build 设为必需检查；不做造成必需检查缺失的路径过滤。
- main push：同样构建，通过后由依赖 build 的 deploy job 发布其 artifact，不重新构建。手动触发也只允许 main 发布。
- Pages 源设 GitHub Actions；deploy 使用 github-pages environment、pages:write 和 id-token:write，官方 configure-pages/upload-pages-artifact/deploy-pages。PR 没有部署权限或正式凭据，不用 pull_request_target 执行 PR 代码。
- main 整条流程采用串行并发组，正在部署不取消；部署前检查构建 SHA 仍是 main HEAD，跳过过期版本。PR 可按 PR 编号取消旧构建。
- Actions 在实施时核验官方版本并固定完整 commit SHA，uv/Python 同样固定。首次上线验证项目子路径、导航、静态资源和搜索；构建失败不部署，回退通过 revert main 后重新构建。
- 文档流水线不调用真实 API 或正式数据库；Excel Demo 不作为 docs CI 门槛。

参考：[Zensical 发布指南](https://zensical.org/docs/publish-your-site/)、[GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。

Excel Power Query 使用 PostgreSQL 专用连接器或 ODBC 读取 raw/下游视图；驱动按客户端环境配置。Demo 展示过滤 stale、筛选日期及刷新结果，不开发 Excel 模块。Excel 刷新不触发下载器，也不继承其省流策略。

## 15. 版本与实施 {#section-15}

当前设计始终在 docs/design/ 保存一套完整正文。版本、修订记录、目标软件与历史 Git 链接集中在 [入口](index.md)，章节不单独编号。
软件版本、设计版本和运行时 ApiSpec/spec_version 独立管理，设计版本不代替数据库 schema 或日志格式版本。发布记录说明采用的设计提交及偏离项。
设计与软件均按 SemVer：兼容修复 PATCH、兼容扩展 MINOR；1.0 后不兼容变更 MAJOR，0.x 不兼容变更升 MINOR 并说明迁移。完整评审轮次递增 draft.N，定稿去掉预发布后缀；定稿不等于软件验收。
软件标签使用 vX.Y.Z，设计定稿使用 design-vX.Y.Z；通常不为草案打标签，不移动已有发布标签。
实现先整理配置/文档，再做英文 CLI 和单文件报告，随后过滤器与故障处理，最后完整回归及部署验收；本轮整理不实施新功能。

## 16. 验收与待决事项 {#section-16}

维护者已选择 MIT。原创项目代码与文档采用根目录 LICENSE，第三方材料保留各自许可证。代码许可证不授予 Tushare 数据的再分发权，数据使用及分发须遵循对应提供方条款与授权。
项目元数据和 README 同步声明 MIT；分发产物仍须核对其携带的第三方组件、声明及义务，不能将依赖改称 MIT。[许可证决策与初步核对](../development/licensing.md)记录范围及剩余检查。

当前设计统一验收门槛见 [验收标准](acceptance.md)。本章不再维护第二份勾选清单；各章节的测试场景供该标准引用。

真实 API 日历及错误样例在独立环境验证，不把市场规则推断当完整性证明。第三方分发产物授权检查仍需在发布时执行，日志轮转跨片监看便利方式已移入后续 backlog，不属于本版范围；不得虚报完成。
