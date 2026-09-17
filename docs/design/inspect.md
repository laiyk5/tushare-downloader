# 本地数据集 Inspect

归属 [当前设计](index.md)，对应 [BL-012](../development/backlog/index.md#bl-012)。基础契约来自 v0.4.0 / revision 2；本次合并 revision 5 修订中的总览呈现设计（文档修订，不代表代码已实现）。本章同时定义命令、呈现和测试条件。

## 1. 用户问题与边界

回答“本地有哪些数据集、占多少空间、数据最新到哪天、最近是否拉取成功、结构是否匹配”。这是当前数据库的一次只读观察，不是下载任务管理、历史执行查询或持续监控。不请求 Tushare、不读取日历、不创建下载日志或报告、不自动初始化或修复数据库。

list 继续回答“这个软件支持什么”，离线可用；inspect 回答“这个数据库现在有什么”，日常查询优先使用；schema 回答“软件承诺怎样的表结构”。默认 inspect 按名称列出全部受支持数据集，未初始化的也显示状态，因此不会把“未下载”误解成“不支持”。整体账号与 SQL 读取方式见 [用户数据访问](data-access.md)。三者不互相替代。按块覆盖图仍属于 BL-016；日期端点、行数和成功记录都不证明范围完整。

## 2. CLI

```bash
# 每个数据集一条紧凑摘要：状态、空间、最新日期、最近成功拉取
tushare-downloader inspect

# 一个数据集的详情；i 为 inspect 的别名
tushare-downloader i daily_basic

# 明确要求精确行数，可能扫描整表
tushare-downloader inspect daily_basic --counts

# 纯文字；全局选项仍放在子命令前
tushare-downloader --plain inspect stock_basic

# 离线查看随软件提供的表结构契约
tushare-downloader schema daily_basic
```

inspect 接受零个或一个 API；未知 API 在连接前报参数错误。--counts（-c）必须指定 API，避免无意对全库计数。没有 --watch、任务 ID、--json、独立颜色/进度选项。schema 的具体行为见 [schema 契约](schema-contract.md)。

inspect 使用现有数据库和输出配置，不需要 Token；新增用户偏好 INSPECT_TIMEOUT=5s，作为每个数据集读取事务的总时间预算，正数且不超过 5m。配置解析复用现有优先级和分组，归入本地查询分组；连接仍使用 CONNECT_TIMEOUT_SECONDS。各 SQL 按剩余预算设置 statement_timeout，锁等待不超过剩余预算，避免每一条 SQL 都重新获得完整预算。预算包括 --counts；超时不会自动改成估算值或自动重试。

list、schema 及各级 --help 均可在无配置、无 Token、无数据库时运行，不因无关下载配置无效而失败；输出模式参数仍有效。inspect 读取连接配置但不调用 require_token。配置错误退出 2，连接/权限/结构/超时错误退出 1，中断退出 130。已识别旧结构显示 Migration needed，退出 1 并提示显式迁移；verbose 总览也不展开为逐表详情。成功读出所有请求数据集（包括确实未初始化或无数据）退出 0；部分读取失败保留已取得信息并退出 1。

## 3. 信息的精确定义

| 字段 | 来源与口径 |
| --- | --- |
| Dataset / Table | 注册 API 及 raw.<api>，不枚举或接管其他 schema 的业务表 |
| State | Ready、Not initialized、Migration needed（仅已识别且有受支持迁移）、Incompatible、Permission denied、Timed out、Unavailable；Ready 只表示结构可读且匹配，不表示已完整下载 |
| Schema | 根据库中身份、spec 登记和实际结构校验得到的已安装契约版本；未知或不匹配不能显示 Verified |
| Total size | pg_total_relation_size(raw.<api>)，包含表、TOAST、索引与分配而尚未回收的空间，包括 stale 行占用；不是有效数据净大小 |
| Table / Index size | 单表详情列 pg_table_size 与 pg_indexes_size；与 Total 同属观察时物理空间，不声称并发变化下精确相加恒等 |
| Latest data | 时间范围 API 中非 stale 行的 max(trade_date)；无 active 行显示 No active data；快照显示 N/A (snapshot)，不使用 list_date 代替 |
| Last successful fetch | meta.slices 中该 API 已持久化的 max(last_success_at)，包括成功空响应；这是成功入库记录携带的请求时间戳，不是 PostgreSQL 精确 COMMIT 时刻 |
| Last recorded attempt | max(last_attempt_at)；同一最大时间戳对应多块时同时呈现各 outcome 计数，不任取一块。只代表已持久化尝试，不包括仍在请求或未能记账的失败 |
| Active / Stale rows | 仅 --counts 执行精确 COUNT FILTER；未请求显示未测量或省略，不把统计估算数冒充精确数 |

统一使用带 UTC 标识的 ISO 时间；业务日期不做时区平移。Never 表示有效元数据内无对应记录；Unavailable 表示读不到，N/A 表示不适用；不能都显示为 0 或一个无说明横杠。已初始化空表仍有真实物理空间，空间为 0 也不用于判定空表。

失败会更新 last_attempt_at 但不能推进 last_success_at；跳过、交易日过滤、dry-run 和初始化不推进二者。仅部分块成功时，最大成功时间仍可能很新，因此不能给整个数据集贴 Up to date 标签。meta.slices 是每块最新观察，不是完整尝试历史；旧 spec 的时间可以展示，但须标注记录版本不兼容，不能用于声称当前契约已成功下载。

已有代码在逻辑块请求前取 stamp，随后与结果持久化。本版保留该语义，不为了展示增添尝试历史表、精确提交时间字段或后台计数器。程序 COMMIT 确认丢失后，inspect 只能展示数据库里实际可见的结果，不能恢复客户端是否收到确认。

## 4. 读取、权限与大库行为

1. 先只读检查数据库身份和内部结构版本，准备阶段同样受一份 INSPECT_TIMEOUT 预算限制，不使用无限等待。没有 meta.schema_info 且没有受管理命名空间时显示 Database not initialized；已有 raw/meta 却没有有效身份时显示 Unmanaged/Incompatible 并退出 1，不推荐直接接管。
2. 有有效身份时，仅对选中的受支持 API 检查登记与真实表。未登记且表不存在为 Not initialized；登记与对象不一致、同名外部对象、列/键不符为 Incompatible。未知的已登记 API 只列为 Other registered datasets 的名称和数量，不尝试用当前软件解释其结构或查询数据。
3. 每个 API 在短 READ ONLY、REPEATABLE READ 事务中读取目录、业务日期和元数据，不获取下载器的排他 advisory lock。以 savepoint 隔离可独立字段的错误，能保留已经取得的空间等信息；事务失效时回滚该 API 并说明缺失。不能为了取得部分值继续在已中止事务上查询。
4. 全库概览各 API 的采样时间可能不同；标明 Observed at / observation interval。普通 SQL 数据遵循各事务快照，物理文件大小不属于 MVCC 快照。允许下载并发，不保证全库某一瞬间的一致状态；与 DDL 的锁冲突受时间预算限制。
5. 默认不执行 COUNT、不扫描业务字段取样、不读取日志文件，也不为 inspect 执行 ANALYZE/VACUUM。复用现有 trade_date 索引查询最新 active 日；stale 密集时仍可能扫描大量索引/行，meta 聚合也随块数增长，不能保证 O(1)。预算耗尽显示 Timed out，并建议缩小到一个 API 或在配置中提高预算。
6. 只读角色需要数据库 CONNECT、raw/meta 的 USAGE、所选 raw 表和 meta.schema_info/meta.slices 的 SELECT；不需要写权限、超级用户或全局统计角色。权限不足有明确缺失对象诊断，不泄露连接密码。若数据库策略限制空间函数，空间标 Unavailable，其他已读字段保留，退出 1。

schema 静态查阅不依赖上述权限。inspect 面向具备元数据读取权限的 reader；只有 raw SELECT 的下游角色仍可直接查数据，但不能宣称完整 Inspect 可用。升级指南应提供现有 reader 的最小授权说明，不自动提升权限。

## 5. 英文输出草图

以下是设计样例，不是实际数据库事实或验收证据。Rich 默认使用标题、表格、状态色；颜色始终配文字。零数据不是警告，结构问题使用警告/错误强调。

### 5.1 缺省总览：一条数据集摘要

```text
Local datasets · tushare
Dataset       State              Size      Latest data  Last fetched (UTC)
adj_factor    Not initialized    —         —            —
daily         Ready              1.24 GiB  2026-09-17   2026-09-17 08:10
daily_basic   Ready              2.08 GiB  2026-09-17   2026-09-17 08:07
stk_limit     Ready              32 MiB    2026-09-17   2026-09-17 08:05
stock_basic   Ready              3.2 MiB   N/A          2026-09-16 09:00
suspend_d     Migration needed   820 KiB   —            —

Observed at: 2026-09-17T08:15:00Z
Size includes indexes and stale rows. Last fetched means last successful fetch.
Ready does not imply complete or up-to-date data. N/A = snapshot; — = not inspected/not initialized.
Details: tushare-downloader inspect DATASET
```

默认仅五列：Dataset / State / Size / Latest data / Last fetched。一个数据集一条逻辑记录，按名称排序。Size 使用 Total size 口径；Last fetched 包括成功空响应，不显示最近失败时间冒充成功。总览时间可按分钟紧凑显示 UTC（不是向上取整）；详情保留完整 ISO UTC 时间。不引入持续更新的相对时间或后台刷新。

空表为 Ready 时，Latest data 显示 No data，Last fetched 无记录显示 Never；快照为 N/A。未初始化／为安全而未检查的字段使用 — 并以 State/脚注解释；权限或超时导致未取得字段须显示 Unavailable 或简短错误标识，不与 Never 混淆。结构不兼容时不为填满摘要而读取未验证业务字段；Migration needed 不宣称字段完整可读。

Rich 使用紧凑表格和状态色，不为每个 API 打印标题、面板或详情卡片。plain 使用相同五字段的紧凑静态文本，无 ANSI/OSC/框线。120 列尽量单物理行；80/40 列允许一个摘要记录换行并使用续行缩进，完整名称、值和状态不得被省略或截断，**不退回每数据集详情卡片**。固定宽度下不可能保证五列始终占一物理行，优先保留信息。异常在 stderr 用数据集名关联简短原因；完整诊断可由指定数据集查看。

### 5.2 指定数据集：完整详情

`inspect API` 按 Identity / Storage / Data & requests 分组，展示完整表名、installed/expected schema、采样时间、表/索引/总空间、最新有效数据日期、最近成功拉取、最近尝试及 outcome。`--counts` 仅为这一数据集附加精确 active/stale 行数。无参数总览不得触发精确计数，保留既有读取预算与索引查询规则。

quiet 保留总览五字段／详情主体及全部异常，只省辅助提示；verbose 总览仍保持一条数据集摘要，额外诊断集中在表后，详情可增加内部版本和查询耗时。不打印秘密。耗时读取可有遵循 PROGRESS 的 spinner，无百分比/ETA 或滚动下载日志。

### 5.3 list 与帮助页

保留 `list` / `ls`，用于尚未配置数据库时离线发现支持集合；不连接数据库、不检查本地存在性，不显示虚构的 Ready/大小/时间。帮助页分别写 `List supported datasets offline.` 与 `Summarize datasets in the configured database.`；inspect 子命令说明零参数为摘要、一个参数为详情，提供这两个示例。不新增 summary 模式开关，不将 list 废弃或重定向成联网命令。

主体写 stdout，警告与错误写 stderr；部分结果的总体摘要标 Partial inspection，不能输出 Complete。无论模式均不生成日志、报告或新目录，调用者可直接重定向终端文字。

## 6. 实施建议

新增一个小型 inspection 模块承载只读结果模型和读取函数，复用 registry/结构校验但不要复用会 require writer 或全局拒绝后无法展示详情的入口。呈现层接收事实模型，不从颜色/文案反推状态。保持下载流程不变；不引入通用查询插件框架。

## 7. 测试条件（先于实施）

| 编号 | 输入等价类与边界 | 通过条件 |
| --- | --- | --- |
| IN01 | 零/单 API、别名、未知 API、无 API 的 --counts | 命令语义一致；参数错误连接数为 0；list/schema/help 无配置可运行 |
| IN02 | 无初始化、合法空表、只有 stale、正常日频、快照 | 各状态、Latest data、N/A、Never 和空间口径正确；不推断完整性 |
| IN03 | 成功非空/空、失败晚于成功、同时间多 outcome、跳过/过滤/dry-run | 最近时间与数据库实际记录相符；失败不冒充成功，跳过不推进时间 |
| IN04 | reader 权限足够、缺 raw/meta 权限、受限空间函数、身份损坏 | 最小权限可用；拒绝状态与 Unavailable 明确；无自动 GRANT/初始化 |
| IN05 | 两连接下载与 inspect、DDL 锁等待、超时、中断 | 不取 writer 锁，不阻止正常块写入；预算有界；部分结果保留；退出码正确 |
| IN06 | 无 --counts / 有 --counts，含 stale 和 NULL 日期约束夹具 | 默认没有 COUNT；精确计数与独立 SQL 一致；无 ANALYZE/VACUUM/HTTP/文件写入 |
| IN07 | 零参数总览／单 API 详情、六输出模式、40/80/120 列、长值与部分失败 | 默认仅五字段，每数据集一条逻辑摘要、无逐表详情卡；窄屏换行不丢信息；plain 无控制序列；quiet 保留主体；详情才展示版本/空间拆分/最近尝试；不改变退出码 |
| IN08 | 已登记旧/未知 spec、结构漂移、未登记同名表、部分 API 缺失 | installed/expected 与兼容状态准确，不将软件支持版本冒充库版本 |
| IN09 | 可重复合成小库/大库，至少五轮，正常与 stale 密集数据 | 记录规模、索引、查询计划、耗时/超时及并发影响；默认无精确计数且预算生效，不设虚构固定延迟 |

性能夹具使用真实独立 PostgreSQL，不访问正式库；元数据/空间以独立 SQL 对照。时间故障用可控时钟，线程/连接并发用同步点，不能靠随机 sleep 证明不阻塞。机械验收由开发者／代理负责；复用未变查询与权限证据，仅补总览/详情差异和代表宽度输出断言。用户主观体验反馈可选，静态样例不替代执行证据。不为本次布局改动重跑完整数据库性能矩阵。

## 8. 依据

- [PostgreSQL 数据库对象大小函数](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-ADMIN-DBOBJECT)：用于定义物理空间口径。
- [PostgreSQL 事务隔离](https://www.postgresql.org/docs/18/transaction-iso.html)：用于定义各 API 的读取快照边界；全库一致性和预算是本项目的设计取舍。
