# 数据库设置向导

归属 **v0.4.0 / revision 6 定稿**。沿用已实施的顺序问答核心，新增 [顺序版本迁移](database-migrations.md)。本次变更已获定稿实施授权；历史标签及证据不变。关联：[UI](database-setup-ui.md)、[headless](database-setup-headless.md)、[验收](acceptance.md)。

## 1. 职责和交付范围

setup 使所选连接及数据库达到当前软件可用状态：读取配置，检查事实，询问缺失信息，预览必要变更，经授权执行，再分别报告数据库/账号/配置结果。用户不选择“初始化还是升级”，程序据事实分流。

| 本版交付 | 本版不交付 |
| --- | --- |
| Click 顺序问答、编号编辑；Rich 语义配色及同流程 plain | 全屏 TUI、焦点/页面导航、独立 plain 状态机 |
| 自动检查；新连接、复用、初始化、补独立 API 表及最小权限 | 安装 PostgreSQL、服务/网络/认证规则管理、备份工具、密码重设 |
| headless 只读检查及显式 apply；共用业务核心 | SQL/Bash 操作包生成、可持久化任务、resume、通用规则引擎 |
| 按明确格式保存配置，保留可识别的无关内容 | 任意 dotenv 格式无损编辑、管理多个连接的配置仓库 |
| 旧/新数据库识别，setup 内经确认按版本顺序迁移 | setup 内隐式迁移、自动 schema diff/修库、通用迁移框架 |

当前软件版本不同不代表数据库需迁移；现有实际迁移为 suspend_d spec 1 → 2，其他五表不变。原候选的脚本导出入口从本设计移除，人工 SQL 指南和 init-db 保留。变化涉及尚未发布的候选功能，实施时同步帮助及用户指南，不能改写历史记录。若后续真有独立需求，再规划复杂快捷键或导出，不为可能需求预留框架。

## 2. 配置和启动检查

使用 -c 指定文件或默认 .env，启动时逐键环境覆盖文件。交互明确编辑后，以会话快照用于本次检查/执行；日常加载优先级不变。新连接和不存在的 -c 路径按[界面设计](database-setup-ui.md#session-configuration)处理。PGHOST、PGPORT、PGDATABASE、PGUSER、PGPASSWORD、PGSSLMODE 保持现有日常连接语义。新增可选 **SETUP_READER_USER=tushare_reader**，仅用于 setup 识别研究账号，可保存在 Database access 分组；不改变下载连接。不要通过猜测“第一个有 SELECT 的角色”自动选择 reader。

“有配置”指文件/环境实际出现受支持 PG* 连接键，而非文件存在；仅 Token 不算，库名/账号等只有一部分时保留并补齐，默认值不是已配置事实。普通 DATABASE_URL 不支持，值不显示也不删除；仅此键时先说明不支持，再收集 PG*。无效/歧义配置先修正或另存新文件，不跳过原配置默默连接 localhost。PGPASSWORD 缺失不等于必然不能连接，保留已有连接层允许的认证机制；读取凭据也不自动保存到新文件。

无配置直接新连接。已有可用连接信息时，输出端点和 Checking，自动只读检查一次；不每次击键查询。启动阶段只读取数据库身份、目录和必要权限，不调用 Tushare、不扫行情/统计行数、不校验数据覆盖；发现明确迁移路径后，进入独立有界只读预检，必要行检查与期限见迁移章。结果分项：

| 结果 | 定义与下一步 |
| --- | --- |
| Ready | writer 真实连接、身份、实际结构、所有权及必需能力符合，reader 角色/授权符合；未改配置直接结束；新连接用 setup --new |
| Migration needed | 已识别受支持的旧结构；预检全部步骤、展示迁移计划并按模式授权，执行后继续必要补齐 |
| Needs configuration | 已证明缺库/表/账号/权限，或输入缺失；列出缺项并仅请求所需信息 |
| Unknown | 网络/认证/超时/检查权限不足，不能确定事实；修正凭据、重查或提供更有权限的检查连接 |
| Unsupported | 外部占用、未知/过新版本、结构漂移、角色冲突；解释人工路线，不自动接管 |

Ready 不等于 reader 已登录验证：初次只检查 reader 角色和授权，单独标 Reader login: Not checked，不为重复检查索要密码。reader 缺失时可同时显示 Downloader ready / Reader setup incomplete，汇总仍为 Needs configuration。使用只读 SELECT/目录检查判断能力，不在真实用户表做写入探测。不能证明能力就 Unknown，不当作 Missing。

状态优先级、迁移预检分类及 headless 退出规则统一见 [迁移输入契约](database-migrations.md#interface)。软件版本、内部 schema_version、API spec_version 和公开契约各有职责；不能用软件版本替代数据库结构版本。无迁移时不因 setup 检查而更新版本标记。

## 3. 用户流程与授权

### 新连接

建立独立内存草稿，保留旧配置及原库。无旧连接时默认 .env；从已有配置使用 setup --new 时，默认目标保存到所选目录下未占用的 `.env.new`（冲突用 `.env.new.1` 等，保存时再检查）；writer 密码不从旧连接自动复制。用户填写服务器/目标名，管理凭据仅在必要时提供；先连接已存在的维护库 postgres（可改），再检查目标。目标已存在且符合规则就复用，不把“新连接”当作“必须新库”。本版不是连接档案管理器；使用新文件通过 `-c` 指定。

### 已有连接

Ready 且本次未修改配置直接打印摘要退出；从修正流程到达 Ready 时仍提供独立保存或放弃修改，编辑后的连接必须先重新检查。缺项时复用已知设置；仅需要建库/建角色/补权限才请求有相应能力的管理员。缺独立表沿用 writer init-db，不强制请求管理员。未知状态先解释检查失败原因，允许提升只读检查能力或修正连接；有管理员不代表授权修改。

### 编号编辑与确认

顺序问答及编号编辑定义见 [界面设计](database-setup-ui.md)。按字段修改使依赖验证失效；修改后重新检查，不并发运行表单与后台查询。Review 显示对象 Before / After / Action / Impact 和配置来源，未知不伪装为不存在。Apply 前输入目标数据库名确认；配置写入单独确认。修改计划依赖或检查发现外部状态变化，撤销旧确认并重做预览。新用户名必须符合当前名称契约；所有 SQL 标识符由数据库驱动安全引用。

### 凭据

管理员连接仅限本次同一服务器及维护/目标库，不成为 writer。新 writer/reader 密码在创建前提供并重复确认。显式高级无密码选择须确认服务器采用其他认证方式；不自动改 pg_hba.conf。已有账号密码输入只用于真实连接验证，绝不重设；失败可选择 Replace/Retry/Back，外部管理员设好密码后再验证。角色名或端点改变时丢弃不再适用的临时凭据，不跨服务器复用管理员密码。

已存在账号尽量先验证登录；新账号须创建后在有 CONNECT 权限的维护库或目标库验证。维护库拒绝 CONNECT 不等于密码错误。完整 reader 登录验证只在本次创建/授权或用户主动验证时要求；无 DB 变更的重复 Ready 检查不重复索取秘密。需要写入的计划开始前先收集后续已知必要凭据；凭据齐全不代表新账号已验证成功。

## 4. 数据库复用和允许操作

| 现状 | 允许行为 |
| --- | --- |
| 确认库不存在 | 创建兼容 writer/reader，建库 owner=writer，writer 初始化，授权、验证 |
| 合法 application_id/database_id、支持的 schema/spec 和结构 | 复用身份及 owner，只补注册 API 的独立缺表或必要授权 |
| 既有真正空库且 owner 已为选定 writer | 无用户 schema/表/视图/函数（标准空 public 允许），明确 Adopt empty database 后初始化 |
| 非空未登记库、占 raw/meta、空库 owner 不符 | Unsupported；另选目标或管理员人工整理，不 ALTER OWNER/清空 |
| 合法受管理库内有 analysis 用户对象 | 正常保留；不以新库“空库规则”阻断 |
| 结构漂移、未知版本、受管理对象非 writer 所有 | Unsupported，不自动按差异修复 |

角色跨整个实例共享。新角色 LOGIN、非 superuser/createdb/createrole/replication/bypassrls；writer 与 reader 不同。复用角色检查属性、继承/SET ROLE 通路、目标库所有权和权限；不更改属性、成员关系或密码，不自动 REVOKE 其他应用/PUBLIC 权限。reader 存在提权通路或无法证明安全时要求管理员检查。不能声称枚举了所有其他数据库依赖，Review 显示检查范围和共享影响。

有限动作：create_writer、create_reader、create_database、initialize_missing_tables、migrate_step、grant_reader_access、verify_access。逻辑复用现有 Store/连接/初始化，动作按依赖固定排序，不引入通用 DAG 调度器。grants 精确到目标库 CONNECT、受支持 raw/meta USAGE/SELECT 及真实 writer 的未来 raw 表默认 SELECT；计划不把“统一再执行一遍 GRANT”当成必要差异。不扩大 reader 数据范围到未知用户对象。

## 5. 核心组织与并发

交互问答、headless 共用四个普通服务边界，无插件注册系统：

| 边界 | 输入→输出 |
| --- | --- |
| 配置读取 | 路径/环境→有效设置、逐键来源、文件原始快照；秘密另存内存、不进入通用 repr |
| inspect | 设置/可用凭据→事实、Unknown 项、原因码、已验证身份 |
| plan | 事实/软件要求→有限动作列表、必要输入、前置条件、脱敏 Before/After |
| execute | 已确认计划/凭据→步骤事件、最终或部分结果 |

复用现有 setup_service、setup_config、setup_db、bounded 及 headless；将 Textual 适配替换为 Click 问答适配。业务服务不依赖交互框架；API 表要求来自现有注册表。Demo 不直接翻译为业务代码，不新增第二套 SQL 或权限规则。

计划只在当前进程存在；包含有效目标/角色、database_id 或不存在事实、相关结构/权限事实的快照。执行前及每个动作前复查相关前置条件；无关行情行变化不使计划失效。不同进程竞争创建对象或计划已变就停止重查，不能把同名竞争结果自动认作本次创建。迁移链的持锁与逐步事务见迁移章；初始化保留原 writer 锁/事务规则；不为 setup 发明全局任务锁。

交互逐步调用共用有界服务；一次只处理输入、检查或执行之一，不并发编辑，不需要 generation 或迟到 UI 响应管理。保留隔离工作进程以保证 DNS/失联期限；退出回收工作进程并恢复密码输入的终端回显。

## 6. 提交、失败与期限

CREATE DATABASE 独立提交；角色/权限按动作事务；缺表初始化沿用 writer 锁和单事务。不是整体原子操作。结果区分 Completed、Failed、Not attempted、Unknown；已完成对象保留，不自动删除“回滚”。结果确认丢失不重发写入，最多做一次只读复核；无法确认保持 Unknown。

交互问答 可修正认证只重验，或 Recheck and review 生成剩余计划重新确认；headless 失败退出，下一次从数据库事实开始，无 resume/账本。配置保存失败不撤销数据库。执行中取消先停止安排后续动作，取消当前操作并在预算内收尾；若不能确认服务器回滚，显示 Unknown。Ctrl+C 的摘要不承诺服务器已经停止。

连接使用 CONNECT_TIMEOUT_SECONDS（默认 10 秒），单主机；检查/验证服务端预算 INSPECT_TIMEOUT（默认 5s，最多 5m），一次检查/验证阶段的客户端总预算为连接预算加检查预算；同一阶段中的账号切换/多次连接共享该剩余预算，不为每次连接或每条查询重新计时。变更步骤 SETUP_STEP_TIMEOUT（默认 60s，最多 10m）包含连接、SQL 与提交；锁等待最多 min(5s,剩余预算)。DNS/失联必须由客户端期限覆盖，不只依赖 statement_timeout。人工等待不计入预算；操作按客户端期限结束，不能无限等待；无需维持可编辑的后台表单。

## 7. 配置保存

交互问答 可保存确认过的 PG* 和 SETUP_READER_USER；writer 密码独立 opt-in，管理员及 reader 密码不保存。未选择保存新密码时，现有目标文件中的旧 PGPASSWORD 保持原样；UI 必须显示它是否与本次验证连接不同，不把“未保存新密码”解释成已删除旧密码。若用户要清除旧值，须单独明确选择并在差异中确认；另存新文件则默认不带入旧 writer 密码。展示文件旧值、当前环境覆盖后的值、本次选择、拟写值及保存后有效值。若环境仍覆盖，标 Saved, overridden by environment，不声称未来命令与已验证连接一致。切换新文件时显示 `-c` 用法，不修改父 shell 环境。

只自动编辑普通 UTF-8 文件内可明确解析的单行设置。保留未知键、分组和单行注释；重复连接键、多行值、无法解析内容、符号链接、非普通文件拒绝覆盖，允许另选文件，不开发通用 dotenv 编辑器。PG* 在原位置改，缺键加入 Database 分组，reader 名称加入 Database access 分组。普通 DATABASE_URL 保持不动。

保存前比对文件读取快照，变化就重新读取和预览；新文件竞争不得覆盖。采用同目录临时文件、0600 权限、原子发布，临时失败清理，不留下含秘密备份。并发保证范围为可检测的普通编辑和程序自身原子提交；不会声称普通文件系统提供跨任意外部编辑器的事务级 compare-and-swap。测试用同步屏障在复核前注入改变，验证拒绝；新文件发布必须使用不覆盖已有目标的原子机制。文件检查和发布对象限定在用户选择的目录，复核文件类型，不以测试未发现竞争证明不存在所有恶意竞态。

不自动创建缺失的父目录；先让用户更改路径。新配置文件存在性/类型/权限检查与 headless 私密输入规则相互独立。headless 永不写 .env，脚本自己管理配置。

## 8. 命令输出、日志与兼容

交互 setup 默认 Rich 配色，plain/NO_COLOR/TERM=dumb 的行为见 [界面设计](database-setup-ui.md)，不再与 plain 冲突。非 TTY 退出 2 提示 headless；不自动切换到写入模式。--new 仅用于交互新连接，与 --headless 冲突。-q/-v 不删减关键问题与确认。help 与版本查询无配置/DB/日志依赖。

普通终端顺序输出英文摘要：目标、分项结果、已完成和未完成操作、配置保存状态、日志路径。日志路径在第一次检查前打印。headless 输出规则不变；不增加 JSON stdout，自动化读取 JSONL 及退出码。

setup 新增 `LOG_DIR/setup/<UTC>-<random>.jsonl`，与下载日志目录约定一致，但不用下载 Reporter/报告模板，也不生成 report.md。交互打开后立即在界面提供路径，headless 在检查前打印；目录/文件受限为 0700/0600（沿用共享日志目录时不擅改已有权限）。日志在内存按白名单构建，事件最少含 event_version=1、timestamp UTC、session_id（仅关联日志）、seq（会话内递增）、mode、event、action、outcome、reason_code、duration_ms 和脱敏 target。非步骤事件 action 为 null，未完成的时长为 null，reason_code 无原因时为 null；target 仅白名单 host/port/database/writer/reader，不记录连接 URL。plan_created 包含有限动作及脱敏 before/after；每次生成计划分配会话内递增的 plan_seq；plan_created、步骤事件及其验证/结果引用同一 plan_seq。step_started/finished 共享 step_id（本次计划内序号）并含 actor_role，以 (session_id, plan_seq, step_id) 唯一关联步骤；配置保存等不属于计划的事件 plan_seq 为 null；session_finished 包含 exit_code、分项就绪/验证/配置状态及 completed/failed/not_attempted/unknown 操作列表。状态值用稳定英文枚举，event_version=1 内只添加可选字段，不改旧字段含义。事件有 config_loaded、inspection_finished、plan_created、step_started/finished、verification_finished、configuration_saved、session_finished；取消与部分结果纳入 outcome。不记录按键/整份配置/密码/DSN/原始 SQL/驱动异常/异常 locals。日志关联号不是持久执行状态。

日志无法创建时，检查前报错退出 1；运行中写日志失败则停止安排下一写步骤，已发生动作按实际结果打印到 stderr，并返回 1，不因此重试 DB 写入。文件无自动清理策略，本版沿用现有用户日志维护方式。交互问答/headless 用同一事件接口，避免各自记不同结果。

## 9. 实施顺序与维护边界

revision 6 定稿后，按验收 Q 节先写迁移规划、授权及失败边界测试，再接入现有 setup 服务、问答和 headless。复用已实现的 suspend_d SQL 迁移与身份规则，删除独立 migrate CLI，同步英文用户指南、错误提示和帮助。保留已通过的 Click/Rich 交互，不重做界面、不重跑历史 Textual 验收。

新增 API 仍通过注册表和初始化增表，不要求每次新增接口写旧表迁移。软件无自动更新、备份或降级功能。

## 10. 验收条件

DBW 编号保持可追溯，以下是当前共用预期；迁移专属条件由 MG01–MG08 唯一定义，旧证据按适用范围复用。

| 编号 | 等价类/条件 | 通过标准 |
| --- | --- | --- |
| DBW01 | 无/坏/部分配置、help、非 TTY、模式冲突 | 只询问缺项，help 无依赖，冲突退出 2，无隐藏等待 |
| DBW02 | 缺库、管理库、空库、外部库、权限未知 | 分类正确，检查无 DB 写入，不误接管 |
| DBW03 | 拒绝确认、编辑后计划失效、并发创建 | 未授权不写，改变事实不沿用旧确认 |
| DBW04 | 三种账号、角色属性/继承、错身份 | 所有权和最小权限成立，reader 真登录按触发条件执行，无旧密码重置 |
| DBW05 | 每个动作失败/取消/提交未知/重跑 | 保留部分结果，有界等待，无 DROP 回滚、无盲目重放 |
| DBW06 | 兼容旧库、缺独立表、未知结构 | 原身份/数据保留；缺独立表按当前定义创建；已知旧结构走 MG，未知拒绝 |
| DBW07 | 保存拒绝、注释、重复/多行/并发/符号链接 | 精确允许范围，歧义另存，原子私密保存，失败不回滚数据库 |
| DBW08 | 密码、标识符、异常、日志与文件权限 | SQL 安全引用，秘密不进入输出/日志/默认保存，0600 约束有效 |
| DBW09 | 原脚本导出验收 | revision 3 已移除，本轮继续保留历史编号；自动化等价验证转为 H01–H08，不记为已通过 |
| DBW10 | 真 v0.3.0 基线、analysis、reader 缺权 | 数据/身份/用户对象不变，仅授权计划内变更 |
| DBW11 | 真实终端、取消、部分完成 | 人能看懂后果和结果，退出恢复终端，非仅截图 |
| DBW12 | 全新目标、writer/reader 不存在 | 只需服务器及必要凭据可完成初始化，不先要求连接目标库 |
| DBW13 | 文件/环境/default 不同、新旧配置 | 展示来源和拟写差异，无变更不重复写文件 |
| DBW14 | 编辑端点、角色、路径及顺序重查 | 正确撤销相关验证，其他输入保留，旧计划不能执行 |
| DBW15 | 新密码不一致、Keep/Replace/Clear、无密码 | 局部修正，密码无导航保留字，无密码显式确认 |
| DBW16 | 真 SCRAM 无/错/正确密码 | 空/错失败、修正仅重验，trust 不代替密码验收 |
| DBW17 | 创建后认证失败、配置保存失败 | 结果分项，重查只提剩余动作，文件失败只重试文件 |
| DBW18 | 40/80/120 列顺序问答、长字段、plain | 可操作、无关键截断、状态不靠颜色，与 UI01–UI04 联合 |
| DBW19 | 仅 Token、仅 URL、PG* 环境、部分键 | 无配置/不支持/部分准确区分，不擅连默认服务器 |
| DBW20 | Ready、reader 缺失、未知权限/网络 | 启动有限目录检查；Ready 不扫数据，无不必要凭据请求；迁移预检见 MG |
| DBW21 | --new / 修改菜单新连接、目标已存在 | 原文件原库保持，新草稿可复用，覆盖独立授权 |
| DBW22 | 软件版本不同、schema 标记不符或无路径 | 不把软件更新当迁移，不输出推测 DDL |
| DBW23 | 改配置后 Ready、保存后环境覆盖 | 仍能预览和保存，准确说明生效值与凭据来源 |

联合 [UI01–UI04](database-setup-ui.md) 与 [H01–H08](database-setup-headless.md) 后验收。当前为 revision 6 定稿，不宣称新增迁移编排已经实现；原型及自动检查均不能替代隔离 PostgreSQL、真实终端及最终软件回归。

## 11. 修订与兼容边界

本轮不回滚代码、不移动 design-v0.4.0-r3、不重写历史验收。revision 6 改迁移编排，交互形态沿用 revision 4；权限、身份、结构检查、部分提交、超时和文件安全继承。旧 UI 失败记录仍有效，不能因为替换方案删除。

新增 --new、允许交互 plain、Ready 直接结束及取消全屏属于明确行为变更，先定稿后实施。不将软件版本差异视为升级依据；revision 5 按实际 suspend_d spec/结构识别迁移需求。当前数据库核心也不能仅凭既有测试通过就声称新问答已经通过验收。

## 12. 验收执行口径（revision 4 继承与适配）

DBW/H/UI 是需求索引而非“一行一个测试”。执行记录必须把每个编号映射到具体用例与证据，写出输入类别、动作、预期及实际结果；多个编号可共用同一夹具，不重复写三套 SQL 测试。

### 最小数据库场景集合

| 场景 | 必查结果 | 关联条件 |
| --- | --- | --- |
| 空实例：库和两账号均不存在 | 按管理→writer→reader真实身份创建/验证，所有者/权限正确 | DBW04/12、H05/06 |
| 当前结构完整库 Ready，自定义 reader | 默认无 DB/文件写入；reader 登录 Not checked 有说明 | DBW10/20、H04 |
| 库就绪但 reader 缺失/缺权 | 分别检查授权差异、凭据缺失的写前拒绝及正确补齐 | DBW02/04/16、H06 |
| 缺独立 API 表，reader 默认权限正确 | writer 可单独补表；无不必要管理员或 reader 登录要求 | DBW06、H05 |
| writer-owned 空库 / 其他 owner 空库 / 未登记非空库 | 只允许明确接管前者，另外两者保留并拒绝 | DBW02/03 |
| 角色不安全、同名、继承写权限、真实结构漂移 | 不降权/重置密码/猜测修复，指出具体冲突 | DBW04/08/22 |
| 网络不可达、身份认证错误、检查权限不足 | Unknown 和缺项区分，预算有界，不写数据库 | DBW05/20、H04/08 |

每个写动作至少注入“执行前拒绝”“事务内失败”“服务端可能已提交但客户端未获确认”三类故障；CREATE DATABASE 的非事务步骤单独覆盖。使用受控驱动/worker 故障验证调度和输出，真实隔离数据库验证实际回滚/提交和重跑后数据、身份、角色属性/ACL。不能仅靠异常 mock 推断 PostgreSQL 已回滚。取消同时覆盖检查阶段和执行阶段。

### 时间、性能与无写入证据

- 一次自动检查阶段总上界为 CONNECT_TIMEOUT_SECONDS + INSPECT_TIMEOUT；取消/worker 终止测试容许额外 2 秒调度余量，记录是否使用缩短的测试预算。变更阶段按 SETUP_STEP_TIMEOUT + 2 秒验收；额外一次只读复核预算单独记录，不冒称包含在失败动作预算内。
- Ready 检查在预热的本地隔离 PostgreSQL、默认六表环境连续 10 次，记录数据库大小、软件环境和每次耗时；检查服务（不含 交互冷启动）p95 ≤ 2 秒为本地体验目标。超标必须先定位并说明/修订基准后评审，不能静默放宽或把网络故障计为 Ready。远程环境只要求阶段预算，不承诺 2 秒。
- 空行情表和至少一个较大表（10 万行）各做同样检查：SQL 捕获证明没有行情表全量 SELECT/COUNT/MAX 等数据扫描，只读目录及身份；不以两次耗时相近代替查询审查。无写入通过 SQL 记录与对象/配置前后快照联合证明；0 条行情行不能证明没有发生 UPDATE/GRANT。
- 核对重复 Ready/apply 没有 DDL、GRANT、角色密码变化、database_id 变化或 .env 写入；新增表及 reader 补权的允许差异单独比对，用户 analysis 对象保持。

### 文件、日志与秘密

DBW07/H02/H07 覆盖文件缺失/存在/被改/符号链接/目录/无权限/磁盘写失败，测试实际 owner/mode、原文件字节和 headless 不保存 .env。以同步屏障控制并发，不靠偶发竞态通过。用带特殊字符的标记秘密检查 stdout/stderr、JSONL、UI 导出、生成/临时文件和异常路径；writer 显式选择保存的目标文件是唯一允许包含该密码的产物。执行中途日志失败允许最终事件缺失，但 stderr 必须保留已知结果并停止后续写步骤。

日志验收验证 JSONL 可逐行解析、seq 顺序、步骤配对、最终退出码和摘要一致；同会话失败后重新规划并执行时，plan_seq 递增，结果不得归入旧计划；进程强杀不能要求最后一行/最终事件一定存在，消费方遇到尾部不完整按“不完整记录”处理，不当作完成证明。

## 就绪、登录验证与配置保存的结果解释 {#result-explanation}

本节为 revision 7 定稿，尚未实施；交互和 headless 共用以下事实解释规则。

Ready 表示受检查结构与配置满足使用条件，不表示每个账号都完成登录验证。不增加数据库查询或自动验证凭据，底层状态和 JSONL 枚举保持不变，仅改人类可读摘要。

| 已有事实 | 建议英文呈现 |
| --- | --- |
| 配置沿用、无需保存 | `Configuration: Using existing settings; no save needed.` |
| 登录验证已执行成功 | `Writer login: Verified.` / `Reader login: Verified.` |
| 未尝试账号登录 | `Reader login: Not tested in this run.`（writer 同理） |
| headless 无保存功能 | `Configuration: Unchanged (headless does not save settings).` |

Ready 摘要补一句 `Ready describes database readiness; untested logins are listed below.`。
必须按实际原因选择文案：用户拒绝保存、保存失败、配置有修改未保存，不能都说 no save needed。
这些情况保留相应警告及失败状态；不把 not_checked 改成 verified，也不要求用户为 Ready 再做一次验收。
已存在和未保存的新配置亦不可混称 existing settings。交互与 headless 使用同一事实解释规则。

呈现依据使用会话中已有保存／修改／验证事实；必要时补充仅内存的保存原因，不新增持久化状态或更改 JSONL 枚举。选择顺序：保存失败 → 成功保存（保留环境覆盖／有效连接不一致警告）→ 有修改或新连接未保存（说明仅本次会话有效）→ 沿用已有有效设置且无需保存。headless 始终明确“不保存配置”，不宣称配置文件存在。成功保存显示 `Configuration: Saved.`，拒绝保存显示 `Configuration: Changes were not saved.`。退出码、取消和失败优先级保持原规则。

Ready 解释只在 Ready 时出现；failed/unknown/interrupted 的登录结果不能映射为 Not tested。`not_checked` 才对应 Not tested，其他已有验证状态继续准确展示。
