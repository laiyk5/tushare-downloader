# 用户体验反馈修订

**v0.4.0 / revision 7 草案；尚未定稿或实施。** 对应 BL-021。
依据：[三次体验](../development/releases/v0.4/v0.4.0/user-experience/index.md)。
本章只修订下列输出与指引，其他行为继承 revision 6。尚未体验成功下载及长期进度，不能由此推断那些行为存在缺陷。

## 1. 失败原因应留在报告和日志

已观察到：缺少 Token 时终端有具体原因，报告只有 ConfigError，JSONL 无失败事件。

实现建议：在现有下载准备异常出口构造一次小型、白名单化的错误描述，共用于终端、report.md 和 JSONL；复用已有脱敏器，不建设通用错误框架。

- 已知错误以稳定 code、英文 message、可选英文 hint 表达。首个必须覆盖的 code 为 `missing_tushare_token`：
  - message：`TUSHARE_TOKEN is not configured. No remote requests started.`
  - hint：`Set TUSHARE_TOKEN in your selected configuration file or environment, then retry.`
- 报告的 Result / Needs attention 中包含具体原因及下一步；若尚无块结果，省略空的 Block details 表，明确 `No blocks were attempted.`。保留原计划与已存在元信息，不虚构请求或提交。
- 日志增加 `preparation_failed` ERROR 事件，包含 code/message/hint、api、command 和既有时间／运行关联字段。字段为兼容增补；quiet 和 LOG_LEVEL 不得让这个错误事件因终端模式而缺失。
- 已知可安全描述的错误用允许的文案映射；未知错误只输出类别、通用说明和查日志指引，不能直接持久化 str(exception)、连接串、响应体、Token、密码或完整环境变量。现有安全诊断规则保持。
- 每次准备失败只记录一次原始失败事件；日志或报告本身写入失败时，向 stderr 给出安全降级说明及已知结果，保持非零退出，不递归写错误或重做请求。不保证 I/O 失败时仍能落盘。
- 保留现有退出码、原子性与已提交结果。发生在配置加载／参数解析阶段、尚无日志上下文的错误不强行创建运行文件。

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

## 3. 全局选项放错位置时给纠正指引

保持 Click 的全局选项必须位于子命令前的规则。只在现有“未知选项”错误明确匹配已注册全局选项时添加提示；不重新排列 argv、不自动执行、不做模糊匹配。

例：`inspect daily_basic --plain` 保留退出码 2，追加：

```text
--plain is a global option. Place it before the command:
  tushare-downloader --plain inspect daily_basic
```

适用于当前全局选项；提示复用主 CLI 的注册信息，带值选项仅展示占位值（如 `--env-file FILE`），不回显用户完整命令或敏感参数。
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
主帮助的 -q 简述补充 `Explicit query and preview results are retained.`，fetch --dry-run 帮助说明预览不被 quiet 隐藏，用户配置与 CLI 指南同步。
不在每次 quiet 执行时再打印一条解释，避免为了说明安静模式反而增加噪声。

## 6. 有界验收与实施顺序 {#verification}

先按以下条件写有意义的失败测试，再实现。只用模拟错误和隔离测试/开发库，零真实 Tushare 请求，不访问生产、不发布。

| ID | 固定案例与通过条件 |
| --- | --- |
| UX01 | 缺少 Token 的公开下载入口：终端、报告和 JSONL 都含安全原因／下一步；错误事件一次；零请求、零数据库写；无空块表；原退出码保留。对 normal/quiet 覆盖，不复制整个模式笛卡尔积 |
| UX02 | 含虚构凭据的未知异常及报告/日志写入失败：秘密不出现在三个出口；安全降级、非零退出、无递归及请求重试。复用已有 I/O 故障夹具 |
| UX03 | Ready 沿用配置、未测试账号、headless、用户拒存、保存失败和新连接未存：英文解释与实际事实一致；原状态/登录验证调用次数不变。一个 80 列 PTY Ready 样例，其余用确定性输出断言 |
| UX04 | --plain 放错位置给正确位置提示；带值全局选项仅占位；合法 inspect -c 不受影响；未知拼写不猜测；错误退出 2 且无副作用 |
| UX05 | 六接口用途准确、list/ls 等价、无 Token/DB 可用；40/80/120 列和 plain 无数据丢失；quiet 保留名称和用途 |
| UX06 | 主帮助及 dry-run 帮助解释 quiet；原 quiet 输出选择断言保持；没有新增每次运行提醒 |
| UX07 | 当前章节、英文用户指南、CLI 示例同步；严格文档构建、链接及受影响安装后帮助检查通过；旧验收和体验报告不改写 |

顺序：UX01/02（失败可追溯）→ UX03（状态解释）→ UX04–06（发现与纠错）→ UX07。
复用 revision 6 未变化的数据／迁移证据；定向检查通过后，仅对稳定候选执行一次完整自动回归。
所有 UX01–07 有证据且无实际缺陷即停止；不新增实网下载、性能矩阵或人类逐项验收。新增发现只登记，不在目标模式中无限扩张。

## 7. 评审结论与边界

上述变更不改变下载范围、数据库结构、权限或认证政策，无迁移要求；仅增补日志错误事件和调整人类可读输出。
List 默认文本布局会变化，但 API 名和离线用途保持，未承诺按终端行格式提供机器协议。
本稿等待维护者定稿；revision 6 的本地验收只证明原候选，不证明本修订已实施。此稿成为 v0.4.0 目标的新修订后，最终发布需采用实施本稿后的候选证据。
