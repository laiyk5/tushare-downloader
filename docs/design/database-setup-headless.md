# Setup headless


v0.4.0 / revision 6 定稿。自动化仍与交互共用事实、计划和执行核心；[迁移契约](database-migrations.md#interface)定义新增确认选项及版本迁移行为。

## 1. 命令与范围

```bash
# 只读数据库检查；脚本已配置 PG* 和可选 SETUP_READER_USER
tushare-downloader -c ./research.env setup --headless

# 应用有限必要变更；私密文件由脚本或秘密管理工具预先提供
tushare-downloader -c ./research.env setup --headless --apply --credentials-file ./setup.private.json
```

自动化选项为 --headless、--apply、--credentials-file PATH，以及结构迁移确认 --confirm-database NAME（组合、缺失及不匹配规则见迁移契约）；交互 --new 与 --headless 冲突并返回 2；不新增 -y/--force/密码字符串参数。--apply 仅与 --headless 配对；--credentials-file 仅 headless 可用，无此标志不自动搜索凭据文件。普通 setup 使用顺序问答，同样的 .env 不等于写入授权。headless 显式 -c 路径不存在属于输入错误 2；未指定 -c 且默认文件不存在时可用完整环境配置，否则返回缺配置 4。交互问答 允许以不存在的 -c 作为保存目标，这个例外不扩展到 headless。

检查模式只读 DB，输出事实、缺项及必要动作；允许创建脱敏日志，不改 .env/角色/库/表。apply 对当前有效配置的明确目标授权，只有预检查通过且必要输入齐备才开始；不会交互询问、自动覆盖配置、生成 SQL 包或执行未知迁移。不指定凭据文件仍可检查，或在现有账号权限和凭据足够时补独立表、执行已确认迁移；不无条件要求管理员。

## 2. 配置与凭据文件

目标 host/port/database/writer/SSL 仅来自 PG* 有效配置，reader 来自 SETUP_READER_USER（默认 tushare_reader）。凭据文件不覆盖目标服务器，管理员连接沿用同一 host/port/SSL，只可更改管理账号和维护库。

私密文件为普通、非符号链接 UTF-8 JSON，最多 65,536 字节（本版不接受 BOM），当前 OS 用户所有，组/其他用户无权限（0600 或更严），重复键和未知键拒绝。读取后只保留内存，工具不修改或删除源文件；目录管理由调用脚本负责。权限检查针对支持的 WSL/Linux 运行环境，不扩大为原生 Windows ACL 支持。结构固定：

```json
{
  "version": 1,
  "admin": {"user": "postgres", "maintenance_database": "postgres", "password": "EXAMPLE_ONLY"},
  "writer": {"password": "EXAMPLE_ONLY"},
  "reader": {"password": "EXAMPLE_ONLY"}
}
```

以上均为占位符，不能当作建议密码。顶层 admin/writer/reader 可省略；version 必须为 1。version 必须为整数 1（布尔值不接受）；对象字段必须为对象而非 null/数组，user/maintenance_database/password 必须为字符串；allow_passwordless_creation 必须为布尔值。所有层级重复键、未知键和类型错误均返回 2，名称遵循主契约校验；JSON 解码错误不回显原文。admin 有值时必须显式非空 user，maintenance_database 默认 postgres。writer/reader 账号名只由主配置确定，避免两个来源不一致。

password 是字符串，空字符串视为未提供；字段缺失也代表没有补充密码。writer.password 为非空字符串时只对 setup 本次连接显式优先于 PGPASSWORD，不写回文件，摘要仅报告“temporary credential override”，不用值比较输出差异。writer.password 缺失或为空时保留原 PG* writer 认证，不以空值清除；JSON null 不是空密码而是格式错误。创建新 writer 可使用实际选定的非空 writer 密码（来自私密文件或 PG*），无需在两个来源重复填写。reader 不继承任何其他账号密码。admin 没有密码时仅允许连接层已有的无密码认证机制；不得回退使用 writer 密码。实例连接不能把未选定账号的隐式环境密码带入另一身份。

对尚不存在的 writer/reader，非空 password 才可创建；若部署使用无密码认证，替代为该对象 `{ "allow_passwordless_creation": true }`。该布尔键仅允许 writer/reader，不能与实际选定的非空密码同时出现（writer 包括来自 PG* 的密码），冲突返回 2。它只许可创建无密码角色，不更改服务器认证规则，也不保证后续验证成功。对已有账号不改变密码；allow_passwordless_creation 不会授权密码重置。凭据空缺但认证机制尚不明确时需实际只读认证检查，不能把“没给密码”一概当缺输入。

不为 headless 设计交互式密码重试。错误直接脱敏返回，脚本修正私密输入后重跑。缺角色、需创建且没有密码/显式无密码授权时，在任何 DB 变更前返回 Needs configuration；若新账号实际认证失败，则可能已有部分创建，按主契约报告。

## 3. 执行和幂等边界

1. 验证选项、解析主配置及显式私密文件；不加载 TEST/BENCH 数据库配置。
2. 创建私密日志，输出路径，按预算检查事实。若管理账号提供，只用于所需检查/操作，不作为 writer。
3. 打印脱敏计划及目标；缺输入、未知/冲突/无路径先退出。对需要 reader 完整验证的写计划，提前收集 reader 凭据或确定现有认证路径。
4. --apply 才执行允许的必要动作，每步重检前置条件。检查到已就绪且没有动作时不执行 DDL、GRANT 或密码修改。
5. 有创建/补表/补权时验证 writer；本次创建 reader 或改变其授权时验证真实 reader 登录。仅缺表且 reader 有正确默认权限时无需为独立新增表操作重索 reader 密码，目录检查新增表授权并标 Reader login: Not checked。
6. 写摘要和退出码。没有隐式配置保存；临时 writer 凭据验证成功不代表下一次下载器已具备凭据，摘要提示调用者配置日常认证。

重跑从数据库事实重新生成计划，不重用旧计划或持久任务。动作前状态改变停止，不自动扩大 --apply 已计划范围；其他进程已创建对象也不悄悄继续。版本迁移是已声明路径的有限动作，按迁移契约执行；不接受任意 SQL 或未知路径。

## 4. 结果、退出码与输出

| 码 | 含义 |
| --- | --- |
| 0 | Ready / 本次已授权动作及必要验证成功；重复 Ready 的 reader 登录可为 Not checked |
| 1 | 连接/检查/执行/验证/日志/保存运行错误或 Unknown（含部分成功） |
| 2 | 参数、配置语法/值或私密文件安全/格式错误；未执行 DB 变更 |
| 3 | 沿用 writer 初始化锁冲突 |
| 4 | Needs configuration / Migration needed：只读检查发现必要变更，或 apply 缺必要输入；未开始写计划 |
| 5 | Unsupported：身份/结构/角色冲突或无支持路径；未开始写计划 |
| 130 | 中断；已完成及未知动作以摘要为准 |

交互正常无写取消为 0；未解决 Unknown/Unsupported 后退出分别为 1/5，输入错误为 2，锁冲突为 3，部分失败为 1，Ctrl+C/EOF 为 130。恢复成功按最终状态返回 0；数据库就绪后拒绝保存为 0，保存错误未解决为 1。headless 不会因“只读检查运行完成”就把非 Ready 返回 0；0 也不表示 Tushare 数据完整。错误优先：输入问题 2→检查 Unknown/失败 1→Unsupported 5→已知缺项 4；进入写计划后除锁冲突/中断，其余失败按 1，不用 4/5 掩盖部分写入。

stdout 输出英文摘要/计划/步骤，stderr 输出警告错误，-q 保留目标、最终结果、日志路径和失败必要步骤，-v 增加脱敏阶段原因。禁止 JSON stdout 和额外机器输出选项；程序读取主契约规定的 JSONL event_version=1 及退出码。日志模式完全共用，不能记录完整凭据文件或原始异常。身份、权限或网络错误给原因码及安全说明。

## 5. 测试条件

| 编号 | 条件 | 预期 |
| --- | --- | --- |
| H01 | 非 TTY、组合参数、plain、help、输入 EOF | 不提问不阻塞；非法组合退出 2；交互 plain 合法但非 TTY 仍拒绝交互；问答不意外启动；help 无依赖 |
| H02 | 重复/未知 JSON 键、超限、符号链接、错误 owner/权限 | 写 DB 前拒绝；不读取非预期凭据渠道，错误不泄露内容 |
| H03 | 主配置/临时凭据/账号来源混合、已有无密码认证 | 目标不被临时文件改变，身份凭据不串用，override 标来源不展示值 |
| H04 | 各 Ready/缺项/Unknown/Unsupported、锁、中断 | 退出码与表相符，输出/JSONL 分类一致，缺项检查不写 DB |
| H05 | 交互问答 与 headless 相同事实和授权，重跑与并发变化 | 计划相同，最终对象/权限相同，无重复 DDL/重设密码，无扩大动作 |
| H06 | 真 SCRAM、新角色缺密码、显式无密码、已有错密码 | 可提前发现的缺项写前拒绝，认证失败准确保留部分状态，正确凭据可恢复 |
| H07 | 日志开头/中途写失败、日志内容/权限、配置文件快照 | 不泄露秘密，不重试写入，headless 不修改 .env，日志是事件而非重放任务 |
| H08 | 每个动作失败/超时/确认丢失/取消 | 有界终止，已提交保留，Unknown 不伪装失败回滚，无无人值守重放 |

对同一独立夹具比对 交互问答 服务调用与 headless 结果，不为界面复制一套数据库测试。未变核心可引用真实历史证据，但须对照来源提交、代码/依赖/配置与适用范围；新问答和受影响路径必须验证当前候选，最终验收记录组合这些证据，不重标历史。

### 验收补充：输入及身份隔离

- H02：覆盖 65,536/65,537 字节、嵌套重复键、未知字段、version=true、null、错误布尔/字符串、无法读取及读取中路径被替换；以已打开的文件描述符核对 owner/type/mode，拒绝符号链接并限制读取量，不采用“先检查路径再随意打开”的模式。
- H03：分别测试临时非空密码覆盖、空值回落、显式 null 拒绝、密码与无密码创建冲突；writer 身份切换到 reader/admin 时，在隔离环境设置带标记的 PGPASSWORD/PGUSER/PGDATABASE/PGSERVICE，验证程序没有将 writer 密码或默认身份带入其他连接。允许明确绑定所选身份的 .pgpass 等连接层机制，不因未提供密码直接否定无密码认证。
- H04：Ready 可 Reader login: Not checked；缺 reader 返回 4；reader 授权未知返回 1；结构不兼容返回 5；部分写入后网络失败返回 1，不能复用写前缺项的 4/5。运行时仅实际 writer 锁冲突返回 3，输出仍须包含此前完成项。

## 结果文案

人类可读摘要遵循 [共用结果解释](database-setup.md#result-explanation)，明确 headless 不保存配置；状态枚举和退出码保持原契约。
