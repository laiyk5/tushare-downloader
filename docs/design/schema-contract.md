# 稳定且版本化的数据表契约


归属 [当前设计](index.md)，对应 [BL-013](../development/backlog/index.md#bl-013)。当前正文纳入 v0.4.0 / revision 6 定稿；历史 revision 2/5 实现证据分别保留。本文是 [用户数据访问](data-access.md) 的结构兼容性子章节；账号、标准读取方式、一致性及可选视图由父章节规定。目标是让下游知道自己依赖的结构及其变化，而不是为六张表引入通用迁移平台。

## 1. 稳定边界

公开契约覆盖 raw.<api> 的表名、字段名、PostgreSQL 类型、可空性、主键字段与顺序、字段含义/单位及下载器附加字段的语义。所有六个已支持 API 都必须有完整字段表，不只做 daily_basic 样例。日期是 date，代码是 text，数值是无固定精度约束的 numeric；不能为了展示改为 float 或任意指定 numeric 精度。

附加字段为 _is_stale boolean NOT NULL、_stale_at timestamptz NULL、_last_seen_at timestamptz NOT NULL、_updated_at timestamptz NOT NULL。它们参与契约，含义沿用总体设计的写入规则；时间戳是下载观察/写入使用的时间，不承诺精确提交时刻。下游选择有效数据时显式 WHERE NOT _is_stale。

公开读取入口本版为 raw.<api>；可选 analysis 视图由用户维护，不由产品自动创建或纳入本契约。meta 是内部协议，不提供永久稳定的业务查询接口；通过 inspect 查看必要状态。索引名称、物理排序、空间大小、内部 SQL/约束名称不属于公开结构 ABI。主键及 NULL 约束属于契约。源端数据真实性、行永久存在、数值永不修正不属于结构稳定承诺。

下游 SQL 应按字段名显式选择，不能依赖 SELECT * 的列数、位置或物理行顺序；新增字段仍要在变化记录中提醒 Excel/研究脚本可能需要刷新选择。

## 2. 三种编号，各有用途

| 标识 | 粒度与存放 | 何时变化 |
| --- | --- | --- |
| schema_version | 已有 meta.schema_info 的整数；内部 raw/meta 管理协议 | 内部存储协议不兼容时变更；不是每次发版或每新增 API 都递增 |
| spec_version | 已有 ApiSpec、meta.schema_info.specs 与 meta.slices 的 API 版本 | 请求/解析/分块/可重用观察语义发生影响兼容的变化时；保留既有机制 |
| Dataset schema | 每个 API 的公开表契约 SemVer，随软件携带的显式映射与字段定义 | 仅该 API 的公开结构或语义契约发生版本变化时 |

公开 Dataset schema 使用独立 SemVer，是下游数据接口的版本，不是恢复独立设计 SemVer。交付 v0.4.0 和设计 revision 2 不能替代它。数据内容刷新不改 schema 版本；新增其他 API 也不改已有表版本。

初次发布契约时，六个现有 API 均将 (内部 schema_version=1, API 名, spec_version="1") 映射为该 API 的 schema 1.0.0。**1.0.0 表示现有结构的首次明确契约，不表示软件进入 1.0。** 该历史映射保留；当前 suspend_d 的 (1, suspend_d, "2") 映射为 2.0.0，其他五个 API 仍为 1.0.0。由实际结构迁移原子更新 spec，不新增重复版本表或 JSON 列。

映射必须是显式、随包交付且可测试的版本表，不通过把字符串 "1" 自动拼成 "1.0.0" 猜版本。多个请求 spec 可映射到同一个公开契约；同一三元组不能映射到两个结构。未来公开结构或存储语义变化必须有新的可持久化辨识组合（通常递增该 API spec），即使它仅由可空字段扩展造成。仅澄清文字的 schema patch 可将同一结构映射到修订后的文档契约，并保留旧文档记录；不能因此声称库里执行了迁移。

## 3. 查阅和校验

```bash
# 离线列出本软件附带的六个 API 契约版本
tushare-downloader schema

# 离线字段说明；不是当前数据库的查询结果
tushare-downloader schema daily_basic

# 在线核对当前表与安装的软件预期
tushare-downloader inspect daily_basic
```

schema [API] 没有额外别名或历史版本选择器，不连接 DB、读 Token、创建日志/报告；明确标题 Shipped schema contract。无 API 时显示 API/table/schema version/key；有 API 时显示字段名/type/nullable/key/source-or-managed/英文说明及单位。quiet 保留主体，verbose 增加内部版本映射，plain 与 Rich 遵守 Inspect 相同的静态查询输出约定。旧契约查文档与对应 Git 软件标签，无需本版实现任意历史注册表查询。

inspect 根据库中三元组识别 Installed schema，再检查实际表、列类型/可空性/键，显示 Expected schema 和验证结论。已知历史映射仍须依据该版本的结构定义校验；没有该定义则显示 Unknown/Unsupported，而非用当前结构强行解释。初版至少识别 v0.3.0 和当前候选使用的六表原始结构。

版本元数据不是结构正确的证明。手工加/删/改列、改类型、改键、视图冒充普通表等必须判不匹配；额外索引允许存在。metadata 声称新版但结构仍旧版，同样不能通过。类型校验应包含 numeric 的精度/scale 等 typmod，避免把 numeric(10,2) 当作现有无限定 numeric；允许 PostgreSQL 的等价类型别名。

发现未知版本/结构漂移时 inspect 尽量显示已读取的 identity、installed/expected、差异摘要并退出 1；下载与 init-db 仍在写入前明确拒绝不兼容结构。不能根据公开 SemVer 同 major 就自动放行，必须有该软件明确支持的内部版本与结构。

## 4. 版本变更分类

| 变化 | Dataset schema 版本 | 对已有库及用户的要求 |
| --- | --- | --- |
| 说明纠错，不改变字段含义、单位或 SQL 行为 | PATCH | 无 DDL；记录说明差异及其无迁移性质 |
| 新增可空字段且旧字段语义保持 | MINOR | 明确 ALTER/默认 NULL/是否回填、锁与费用；新 spec 识别；旧软件不默认保证兼容 |
| 删除/重命名字段、键或类型改变、单位/含义改变、收紧可空性 | MAJOR | 提供明确迁移和下游改动；禁止静默执行破坏性变更 |
| 新增独立 API 表 | 新 API 从 1.0.0 开始 | init-db 事务增表，旧表和版本不动；按旧增表规则保持数据及身份 |
| 请求规划改变而落库契约不变 | 不变 | 必要时递增 spec_version，说明旧分块记录是否失效及如何重查 |
| 索引维护、数据订正、常规 refresh/update | 不变 | 按实际变更记录维护/数据行为，不冒充 schema 升级 |

源 API 新字段不自动映射入库；显式字段选择和既有解析规则保持不变。新增支持字段先修设计/契约/测试，再实施。源 API 缺失必需字段、错误类型或不兼容响应仍失败，不能用 NULL 填充掩盖协议变化。

数据契约的 major 与软件 major 不必相等；软件版本仍按当前 0.x 规则选择，发布说明明确哪个 API 从哪个契约版本变成哪个版本。公共语义变更即使 DDL 不变也必须可识别、记录升级/重拉或转换方法。

## 5. 单一来源与文档

继续使用显式 ApiSpec/Field 作为当前字段定义，不把数据库 introspection 结果反向当成应有契约。补充契约版本、英文说明/单位及显式历史映射；当前 raw DDL、schema 命令和英文 reference 字段表由同一份定义派生。可以新增小型 contracts 模块，不引入 schema DSL 或额外服务。

实施时生成 docs/reference/schema.md 的六接口索引和字段表，集中附带每 API 的版本变化记录；纳入 Zensical Reference 导航。生成结果纳入 Git，本地检查验证未漂移；当前契约的独立批准快照/期望值用于回归，不能仅比较两个同源生成物就认为正确。包里必须含契约数据，离线安装也能 schema；不额外设计 JSON 终端输出。

每次变更记录 API、旧/新 Dataset schema、首次交付软件版本、字段差异、兼容性、用户动作、迁移说明链接；历史详情由 Git 标签保留。Inspect 显示版本，schema 提供当前说明，升级/发布文档主动列出变化，不另加每次下载都打印相同公告的通知系统。

## 6. 本次升级范围

当前 suspend_d 存在明确的 spec 1 → 2 迁移，数据约束见 [修正方案](api-contract-validation.md#correction)，编排见 [setup 迁移](database-migrations.md)。其余五表和内部 schema_version=1 保持，旧覆盖按版本决定复用。已登记结构漂移必须拒绝，不猜测修复。

来源矩阵、用户操作和恢复只在 [升级设计](upgrading.md)维护；不假设旧软件能读取新键。新增独立表仍可通过 init-db 或 setup 创建，不应改动无关表的版本。

## 7. 测试条件（先于实施）

| 编号 | 输入/变化 | 通过条件 |
| --- | --- | --- |
| SC01 | 六个 API 和四个附加字段 | 离线契约/已批准期望/真实标准 PG 列及主键一致；字段含义/单位完整 |
| SC02 | 无 .env/Token/DB/网络，wheel 独立安装 | schema 与帮助可用，不创建文件、不读数据库；发行包契约资源完整 |
| SC03 | 已知/未知内部版本、同契约多 spec、无登记、元数据与实物矛盾 | 已安装/软件预期明确分离，未知不猜测；兼容失败非零且不写数据 |
| SC04 | 缺/多列、NULL 约束、键顺序、numeric typmod、视图冒充、额外索引 | 契约漂移拒绝；等价类型名和额外索引允许；不因自动生成而刷新期望 |
| SC05 | 文案 patch、可空扩展、破坏性变化、新 API、仅请求变化 | 纯定义夹具验证版本映射与分类；新增 API 不推进其他 API；不把合成迁移执行器夹具当成真实产品版本演练 |
| SC06 | 实际 v0.3.0 标准旧库与当前未发布候选库 | MG06 共用：除批准的 suspend_d 结构/spec 外身份、数据、块记录、原权限保持；inspect/schema 正确，重复初始化幂等；不生成新版本表 |
| SC07 | 未支持的旧/新结构和手工漂移库 | 下载/init-db 在数据写入前拒绝，差异可定位，无自动 ALTER/接管 |
| SC08 | 文档生成、契约历史、六模式及窄屏 | reference 与契约一致，旧记录可追溯；离线/在线标题无混淆，quiet 保留主体 |

SC05 只验证版本策略及兼容拒绝行为，不冒充“未来全部迁移已测试”。SC06 与升级指南共享真实旧库演练，SC03/SC04/SC07 使用独立数据库故障夹具；不得在用户正式库修改结构制造异常。
