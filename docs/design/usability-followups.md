# 用户体验反馈修订

**v0.4.0 / revision 7 草案；尚未定稿或实施。** 对应 BL-021。
依据：[三次体验](../development/releases/v0.4/v0.4.0/user-experience/index.md)。
本章只修订下列输出与指引，其他行为继承 revision 6。尚未体验成功下载及长期进度，不能由此推断那些行为存在缺陷。

## 1. 失败原因应留在报告和日志

已观察到：缺少 Token 时终端有具体原因，报告只有 ConfigError，JSONL 无失败事件。

实现建议：在现有下载准备异常出口构造一次小型、白名单化的错误描述，共用于终端、report.md 和 JSONL；复用已有脱敏器，不建设通用错误框架。

- 已知错误以稳定 code、英文 message、可选英文 hint 表达。本轮仅新增一个已知原因专用映射和一个通用后备；不按全部异常类型扩展错误目录。专用 code 为 `missing_tushare_token`：
  - message：`TUSHARE_TOKEN is not configured. No remote requests started.`
  - hint：`Set TUSHARE_TOKEN in your selected configuration file or environment, then retry.`
- 报告的 Result / Needs attention 中包含具体原因及下一步；若尚无块结果，省略空的 Block details 表，明确 `No blocks were attempted.`。保留原计划与已存在元信息，不虚构请求或提交。
- 日志增加 `preparation_failed` ERROR 事件，包含 code/message/hint、api、command 和既有时间／运行关联字段。字段为兼容增补；quiet 不影响文件事件；现有合法 LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）均应保留 ERROR。不扩大 LOG_LEVEL 取值、不改变其他级别过滤规则。
- 已知可安全描述的错误用允许的文案映射；未知错误只输出类别、通用说明和查日志指引，不能直接持久化 str(exception)、连接串、响应体、Token、密码或完整环境变量。通用后备 code 为 `preparation_error`；message 使用固定的安全阶段说明，hint 指向配置／连接／日历检查指南，不把未写入日志的细节承诺成“见日志可查”。类别只接受程序侧类别标识，不序列化异常对象。现有安全诊断规则保持。
- 每次准备失败只记录一次原始失败事件；日志或报告本身写入失败时，向 stderr 给出安全降级说明及已知结果，保持非零退出，不递归写错误或重做请求。不保证 I/O 失败时仍能落盘。
- 保留现有退出码、原子性与已提交结果。发生在配置加载／参数解析阶段、尚无日志上下文的错误不强行创建运行文件。

### 阶段与证据边界

仅处理下载命令已有 reporter、尚未进入数据块执行时的失败，包括现有日历准备失败出口；共用描述和事件，不重复追加另一条 preparation_failed。既有 invocation_finished 终结事件可保留，终结事件不是第二条错误事件。

`No remote requests started.` 只用于已确定任何远端尝试均为零的缺 Token 场景；日历失败可能已有 calendar HTTP attempts，必须保留实际次数，并说明 `No data requests started.`。未知计数明确 unknown，不能填 0。空块结果不等于零远端尝试。执行阶段失败、KeyboardInterrupt 和提交未知仍走原有路径，不改归类、不丢结果。

已有报告采用安全原因；本轮不重构其他命令的 guarded 异常体系、不改变 API 重试规则。日志初始化失败没有日志文件保证；reporter 已存在时也仅在可写出口保存。

## 2. Setup 的 Ready 需要解释范围

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

## 3. 全局选项放错位置时给纠正指引

保持 Click 的全局选项必须位于子命令前的规则。只在现有“未知选项”错误明确匹配已注册全局选项时添加提示；不重新排列 argv、不自动执行、不做模糊匹配。

例：`inspect daily_basic --plain` 保留退出码 2，追加：

```text
--plain is a global option. Place it before the command:
  tushare-downloader --plain inspect daily_basic
```

适用于当前全局选项；提示复用主 CLI 的注册信息，带值选项仅展示占位值（如 `--env-file FILE`），不回显用户完整命令或敏感参数。纠正样例由固定可执行文件名、注册命令／已知 API 名和占位符构造，不从原始 argv 拼接；未知 API 以 API 占位。长选项 --env-file=VALUE 也只显示 FILE。单独短选项（如 -q/-v）支持提示；短选项串和 -- 之后的参数沿用普通解析错误，不增加拆解器。-h/--help 若已被子命令合法接受，不触发建议。
子命令已合法定义的同名选项按子命令处理，例如 `inspect API -c` 是 counts，不能建议移到前面。
未知 `--plian` 仍走普通错误，不生成猜测。帮助中说明 global options precede COMMAND；运行前即失败，不新增 DB/API 或配置写入。

## 4. List 先说明数据是什么

保留离线 list/ls；默认每数据集一条，先显示 API 名和一句英文用途，再显示简短类型。详细主键及 stale 策略留给 schema／帮助，不默认堆进所有行。

| API | 英文用途 | 类型标签 |
| --- | --- | --- |
| daily_basic | Daily valuation and turnover indicators | Daily |
| stock_basic | Stock listing and reference information | Snapshot |
| daily | Daily prices and trading volume | Daily |
| adj_factor | Price adjustment factors | Daily |
| stk_limit | Daily upper and lower price limits | Daily |
| suspend_d | Trading suspension and resumption events | Daily events |

描述属于随接口注册交付的静态元数据，不查询数据库或平台；类型标签只解释数据，不改只增／可变规则。
API 名和一句用途在 Rich/plain、quiet 下都保留，长行自然换行；不为此新增列表模式或 CLI 开关。
list 与 inspect 仍分别回答“支持什么”和“本地有什么”。用户 CLI reference 与示例随实现同步。

## 5. Quiet 的例外说清楚

quiet 保留用户主动索取的 help/list/schema/inspect/dry-run/clean preview 主体，仍抑制常规过程输出；不改结果语义。
主帮助的 -q 简述补充 `Explicit query and preview results are retained.`，fetch/refresh/update 共用的 --dry-run 帮助说明预览不被 quiet 隐藏，用户配置与 CLI 指南同步。
不在每次 quiet 执行时再打印一条解释，避免为了说明安静模式反而增加噪声。

## 6. 有界验收与实施顺序 {#verification}

先按以下条件写有意义的失败测试，再实现。只用模拟错误和隔离测试/开发库，零真实 Tushare 请求，不访问生产、不发布。

| ID | 固定案例与通过条件 |
| --- | --- |
| UX01 | 缺少 Token 的公开下载入口：终端、报告和 JSONL 都含安全原因／下一步；错误事件一次；零请求、零数据库写；无空块表；原退出码保留。normal/quiet 两个入口案例；dry-run 缺 Token 仍成功且无 preparation_failed。日志级别只对共用事件层验证四个合法值，不与入口模式交叉 |
| UX02 | 含虚构凭据的未知异常及报告/日志写入失败：秘密不出现在三个出口；安全降级、非零退出、无递归及请求重试。复用已有 I/O 故障夹具。固定三类：未知异常夹带虚构秘密、错误事件写入失败、失败报告写入失败；不叠加故障。另复用一个已有日历失败夹具断言保留日历尝试且数据尝试为零 |
| UX03 | Ready 沿用配置、未测试账号、headless、用户拒存、保存失败和新连接未存：英文解释与实际事实一致；另含成功保存受环境覆盖、环境配置无文件和已有失败验证状态；原状态/登录验证调用次数不变。一个 80 列 PTY Ready 样例，其余用确定性输出断言 |
| UX04 | --plain 放错位置给正确位置提示；--env-file FILE 与 --env-file=VALUE 仅占位且虚构秘密不回显；一个单短选项；合法 inspect -c/--help 不受影响；未知拼写、短选项串、-- 后参数不新增纠正逻辑；错误退出 2 且无副作用 |
| UX05 | 六接口用途准确、list/ls 等价、无 Token/DB 可用；固定 40 列 Rich、80 列 plain、120 列 Rich 三组样例；所有六个 API 名和用途可读，换行不混入邻行；quiet 单独一次验证保留名称和用途，verbose 不回退旧布局 |
| UX06 | 主帮助及 fetch/refresh/update 的 dry-run 帮助解释 quiet；原 quiet 输出选择断言保持；没有新增每次运行提醒 |
| UX07 | 当前章节、英文用户指南、CLI 示例同步；严格文档构建、链接及受影响安装后帮助检查通过；旧验收和体验报告不改写 |

顺序：UX01/02（失败可追溯）→ UX03（状态解释）→ UX04–06（发现与纠错）→ UX07。
复用 revision 6 未变化的数据／迁移证据；定向检查通过后，仅对稳定候选执行一次完整自动回归。
所有 UX01–07 有证据且无实际缺陷即停止；不新增实网下载、性能矩阵或人类逐项验收。新增发现只登记，不在目标模式中无限扩张。

### 证据复用与停止点

UX01/02 共用准备异常夹具和安全描述断言；UX03 复用 setup 保存/恢复测试；UX04 单独验证 Click 错误分流；UX05 复用 read-command 输出样例；UX06 只补帮助文案断言，不重跑一个新的六模式业务矩阵。UX07 安装后帮助／list 检查复用同一个离线 wheel 环境。既有回归负责未改变业务不回退。

测试编号是需求分组，不是限定为七个测试函数。实施记录在每个分组下列明上述等价类、结果及引用即可，不新增第二套验收编号。修改后定向重验；稳定候选一次完整回归，纯记录补充不重跑软件测试。所有原本有效的发布 K 门槛继续适用。

## 7. 评审结论与边界

上述变更不改变下载范围、数据库结构、权限或认证政策，无迁移要求；仅增补日志错误事件和调整人类可读输出。
List 默认文本布局会变化，但 API 名和离线用途保持，未承诺按终端行格式提供机器协议。
本稿等待维护者定稿；revision 6 的本地验收只证明原候选，不证明本修订已实施。此稿成为 v0.4.0 目标的新修订后，最终发布需采用实施本稿后的候选证据。


### 2026-09-18 定稿评审

结论：补齐本轮五项边界后，设计合理、自洽且可执行，UX01–UX07 对应五项体验问题及文档交付，无必须增加的真实平台测试；**可交维护者确认定稿**，尚未授权实施。

| 审查点 | 原缺口 | 收口结果 |
| --- | --- | --- |
| 请求事实 | 准备失败容易被误写成所有 HTTP 均为零 | 区分日历与数据尝试；未知不填零；执行失败不改归类 |
| 状态文案 | not_saved 无法唯一推出 no save needed | 按失败、保存、未保存修改、沿用顺序选择；保留环境覆盖与失败验证事实 |
| 选项纠错 | 直接拼命令可能泄露值，短选项与同名选项边界未定 | 使用注册信息与占位值；限定普通未知选项错误分支，不重解析或执行 |
| 验证完整性 | 缺日志级别、dry-run、日历尝试、保存覆盖案例 | 在既有 UX 编号补齐，明确合法级别及有限等价类 |
| 验证重复 | 模式×宽度×故障容易膨胀 | 固定代表组合，共用故障夹具、一个 PTY 和一个安装环境 |

该评审是文档结论，不是软件验收结果；无需为评审运行产品回归或外部 API。
