# 用户数据访问

归属 [当前设计](index.md)，对应 [BL-013](../development/backlog/index.md#bl-013)。当前正文纳入 v0.4.0 / revision 6 定稿；访问能力沿用既有实现，状态见开发记录。原“稳定且版本化的 schema”扩展为用户数据访问规范；[schema 契约](schema-contract.md) 是本设计的结构兼容性子章节，原链接保留。

## 1. 目标与默认路径

用户用只读数据库账号，通过 PostgreSQL 客户端、Python SQL 或 Excel 等工具查询本地数据。产品应明确：使用哪个账号、查哪些对象、哪些字段及语义可以稳定依赖、如何识别 stale、升级后哪里查变化。仅给出表结构版本不能完整回答这些问题。

默认路径为 **tushare_reader → raw.<api> → 显式选择字段及 stale 条件**。数据库仍为 tushare；连接位置、端口、TLS 和认证沿用实际部署，不在设计中假定所有客户端都能用 localhost。下载账号与阅读账号分别配置，不能把 writer 密码复制给 Excel/研究脚本。本版不增加 REST 服务、专用读取 SDK、SQL 代理或自动导出层。

| 对象 | 定位及稳定性 |
| --- | --- |
| raw.<api> | 下载器维护的公开读取表；全部六个 API 的列、类型、键、单位、附加字段按 Dataset schema 契约管理 |
| meta.schema_info / meta.slices | 内部管理对象；只为 Inspect 等工具提供必要只读权限，下游研究代码不应依赖其长期结构 |
| analysis.<view> / 用户研究表 | 可选、由用户或管理员维护；产品不创建、不覆盖、不清理，不纳入产品 Dataset schema 版本 |

PostgreSQL 的 schema（raw/meta/analysis 命名空间）和 Dataset schema（表结构契约）是两个概念，帮助和文档需明确区分。

## 2. 账号与只读边界

管理员创建账号并管理凭据；init-db 创建/校验下载器对象，不创建登录账号、不改密码、不自动 GRANT。测试仍使用独立数据库和角色。

| 能力 | tushare_writer | tushare_reader |
| --- | --- | --- |
| 下载、更新、初始化、清理 raw/meta | 按既有设计允许 | 禁止 |
| 查询 raw 和运行 Inspect | 允许 | 允许（Inspect 需要下述两张 meta 表读取权限） |
| INSERT/UPDATE/DELETE/TRUNCATE、ALTER/DROP 受管理对象 | 允许的维护路径 | 禁止 |
| CREATE 对象或接管 raw/meta | 管理范围内 | 禁止 |
| 创建 analysis 研究结果或视图 | 不作为下载器职责 | 使用另一个有相应权限的研究/维护账号，不能扩权只读账号来兼任 |

reader 必须是 NOSUPERUSER、NOCREATEDB、NOCREATEROLE、NOREPLICATION、NOBYPASSRLS，不拥有数据库、schema、表或视图，不继承或能 SET ROLE 到 writer/其他写角色。只授予 CONNECT、必要 schema USAGE 和对象 SELECT；不授予写权限、schema CREATE 或对象权限的 grant option。

“只读”的承诺是不能修改持久业务/管理数据及其结构；不是隔离任意 SQL 的沙箱，不保证重型 SELECT 没有资源影响。不能只设置 default_transaction_read_only 就宣称权限隔离：用户可改变会话设置，真正边界必须由有效权限及对象所有权实现。允许默认临时对象权限不等于允许写 raw/meta；若部署要求完全禁止临时对象，由管理员另行配置，不扩大本版承诺。

管理员需检查既有 PUBLIC 权限、角色继承、对象所有权，以及自定义可写 SECURITY DEFINER 函数等额外授权通路；不因一个角色名叫 reader 就判定只读。新建标准库按本节验证；共享或手工改过的库不能由工具直接 REVOKE PUBLIC 或批量撤销其他应用权限，应先报告差异并由管理员处理。

## 3. 最小授权与升级

以下是实施后应收入英文运维指南的 SQL/psql 模板，不是 Bash；角色不存在时由管理员创建并使用交互式密码设置，不把密码写入版本库或示例命令行。对象由已知 tushare_writer 创建，数据库和 raw/meta 已初始化。现有角色先核对权限，不反复 CREATE 或擅改其属性。

```sql
CREATE ROLE tushare_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS;
\password tushare_reader
\connect tushare
GRANT CONNECT ON DATABASE tushare TO tushare_reader;
GRANT USAGE ON SCHEMA raw, meta TO tushare_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO tushare_reader;
GRANT SELECT ON meta.schema_info, meta.slices TO tushare_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE tushare_writer IN SCHEMA raw
  GRANT SELECT ON TABLES TO tushare_reader;
```

这份模板授予所有受支持数据集的读取，不是按数据集隔离的授权产品。raw 命名空间只放下载器受管理对象；不要把私有研究结果放进去。仅需要少数数据集的部署可逐表授权而不设全 raw 默认权限；inspect 全库概览会明确显示其余对象无权限，不能静默隐藏成未初始化。

已有仅 raw SELECT 的 reader 仍能执行原有 SQL；要完整运行 Inspect，管理员仅补 meta USAGE 及上述两表 SELECT，不授予未来所有 meta 表权限。default privileges 只覆盖指定创建者未来新建对象，既有表仍需要 GRANT；若实际对象创建角色不同必须按真实创建角色设置。新增 API 的升级验证包含“同一 reader 能否读新表”，不能仅验证 writer 初始化成功。

账号与读取入口本身不要求迁移数据；suspend_d 的结构变化按 [迁移契约](database-migrations.md)处理；账号补权与可选自建视图属于明确的运维动作，不能将“无数据迁移”写成“所有用户无需任何配置”。产品不存储第二套 reader 凭据；用户客户端使用自己的凭据存储，Inspect 可用现有配置文件选择机制指定 reader 连接，并注意环境变量会按既有优先级覆盖文件值。

## 4. 标准查询约定

```sql
SELECT ts_code, trade_date, close, vol
FROM raw.daily
WHERE NOT _is_stale
  AND trade_date BETWEEN DATE '2026-09-01' AND DATE '2026-09-14'
ORDER BY trade_date, ts_code;
```

完整限定 raw.<api>，显式选择字段，参数化传入用户筛选值；不依赖 search_path、SELECT * 的列数或数据库默认排序。默认研究示例过滤 NOT _is_stale；需要诊断撤回/历史保留行时显式查询 _is_stale，不另造重复数据副本。

这里的 active 只表示下载器未标记 stale，不等同于股票正在上市、当天交易或业务上“有效”。例如 stock_basic 的退市股票可以仍是非 stale，是否排除取决于用户按 list_status 筛选。数据日期、字段单位和 NULL 含义必须查契约；不默默进行复权、补零、单位转换或跨表清洗。

结构稳定不保证内容不变：refresh/update 可修正值、插入新键、标记或恢复 stale；用户授权 clean 会删除行。单块事务原子提交，但长下载、多 API 并非整体原子刷新。普通读取可能看到部分块已更新；多条查询需同一数据库快照时可显式使用短 REPEATABLE READ READ ONLY 事务。这能固定已提交数据的观察快照，不能使尚未完成的多个下载变成同一次源端快照。长事务可能影响维护，应及时结束。

可复现研究需要用户另外保存数据快照/导出及来源时间；schema 版本不是数据版本，产品不承诺历史时点重建。Excel 刷新只读本地当前数据，不触发下载，也不保证多条独立 Power Query 共享一个数据库事务。

## 5. 视图：提供可选示例，本版不强制新增一层

普通 view 是命名查询，每次读取访问底层数据，不复制一份数据；适合保存常用字段选择和 stale 过滤。materialized view 保存结果，需要刷新策略、额外空间及新鲜度管理，本版不提供。视图不自动带主键约束，客户端不能把它当成完整继承基表约束的另一张表。

本版保留 raw.<api> 为正式稳定入口，同时在读取指南提供以下可选示例。这样不为了展示固定过滤就新增六个受管理视图及其版本、授权和迁移生命周期；未来如需默认过滤或隔离内部列，可再评审产品管理的读取 schema，不能届时静默废弃 raw 契约。

下面由具有对应权限的管理员/研究维护账号在自己的 analysis 命名空间执行，reader 只查询。analysis 必须已由维护者创建；同名对象存在时先审查，不用 CREATE OR REPLACE 自动覆盖用户对象。

```sql
CREATE VIEW analysis.daily_active
WITH (security_invoker = true) AS
SELECT ts_code, trade_date, open, high, low, close, vol, amount
FROM raw.daily
WHERE NOT _is_stale;

GRANT USAGE ON SCHEMA analysis TO tushare_reader;
GRANT SELECT ON analysis.daily_active TO tushare_reader;
```

security_invoker 让调用者仍需具备底层表的读取权限；本例不借视图所有者提升权限。即使视图技术上可更新，reader 也没有视图及底表写权限，因此写入必须失败。视图不是安全过滤边界：reader 本来能读 raw，因此仍能直接查看 stale 行。

reader 通过 SELECT ts_code, trade_date, close FROM analysis.daily_active 使用固定入口，不能自行 CREATE/修改视图。下载器更新底表后普通视图无需单独刷新；修改视图列/过滤语义由用户维护者负责。升级文档提醒视图依赖可能阻止将来的破坏性 DDL，不能 CASCADE 删除下游对象；本版通过可选示例验证普通刷新后读取及权限即可，不承诺管理任意用户 SQL。

## 6. 用户入口与文档组织

已同步英文 [用户读取指南](../guide/reading-data.md)，内容仅使用现有 SQL 能力，不提前宣传未实现命令；对应 SQL/权限验收仍按 DA 条件执行，文档写出不代表功能已验收。后续实施继续维护该指南：reader 连接、显式字段与日期查询、stale 含义、读取一致性、可选视图；从 Quickstart/README 链接，不把管理员授权脚本堆进 README。

operations/database.md 负责账号创建、实际授权、未来表默认权限及排错；reference/schema.md 负责六表字段和变化记录，依据 [schema 契约](schema-contract.md) 生成；operations/upgrading.md 说明上版 reader 补权及结构兼容。Excel 只是读取 Use Case Demo，不成为产品主验收工具；用 PostgreSQL SQL/普通客户端即可验证标准访问协议。

schema [API] 解释随软件附带的公开表结构；inspect [API] 展示当前库的事实和结构是否匹配。它们不管理账号或创建用户视图。SQL/连接协议才是数据访问入口，无需额外发明读取数据 CLI。

## 7. 验收条件

下列 DA 条件与子章节 SC01–SC08 共同构成 BL-013 完成要求，不仅交付一份 schema 表。

| 编号 | 场景 | 通过条件 |
| --- | --- | --- |
| DA01 | 标准库，新建 reader 与既有 raw-only reader | 六表 SELECT 成功；仅按文档补权后 Inspect 可读；无 Token、无 writer 凭据即可使用 |
| DA02 | reader 直接写、经可更新视图写、TRUNCATE、ALTER/DROP、CREATE raw/meta 对象 | 独立真实 PG 中全部被权限拒绝；业务数据及结构保持；有效角色无 writer 继承/切换通路 |
| DA03 | 指定创建者新增测试对象、不同创建者、既有表 | 默认 SELECT 只对正确创建者未来对象生效，既有表显式授权；不自动授权全部 meta；新增 API 升级案例验证 reader |
| DA04 | active/stale、退市但非 stale、NULL、日期边界 | 标准 SQL 和视图结果与独立预期相同；不把 stale 等同上市状态、不默认做业务清洗 |
| DA05 | 用户视图随底表修改、reader 经视图读、同名自建对象 | 普通视图反映提交后结果；查询权限正确，写失败；初始化/清理不覆盖用户视图，清理后可读取空结果 |
| DA06 | writer 分块提交时单条查询及多查询只读事务 | 无脏读；固定事务快照可重复；允许已完成块与未更新块并存，不冒称全下载原子快照 |
| DA07 | 真实 v0.3.0 旧库升级、已有研究 SQL/视图 | 数据、原角色能力、原 SQL 保持；补权动作明确；受管理表无 DDL，用户对象不被删除或接管 |
| DA08 | 英文读取/运维/字段/升级指南及 schema/inspect | 入口各司其职，说明和可执行 SQL 一致；本地严格构建，SQL 在独立 PG 验证；Excel 仅 Demo |

权限故障和恶意授权夹具只在独立测试库/角色创建。不能只检查 GRANT 文本或 default_transaction_read_only 值就判定只读；必须实际连接 reader 验证拒绝。默认权限测试的临时对象不能混入生产 raw。性能及布局沿用 Inspect 条件，schema 兼容沿用 SC 条件，不重复增加框架。

## 8. 依据与取舍

- [PostgreSQL 权限](https://www.postgresql.org/docs/18/ddl-priv.html)：SELECT/写权限、所有者与有效授权是访问边界。
- [默认权限](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)：默认权限面向指定创建者的未来对象，不能代替已有对象授权。
- [视图](https://www.postgresql.org/docs/18/sql-createview.html)：普通视图的执行、可更新性和 security_invoker 语义。

本版选择稳定 raw 读取加可选用户视图，是减少产品管理对象的设计取舍，不是 PostgreSQL 的限制。若维护者希望所有用户默认通过产品视图读取，应另在本草案明确受管理视图名、默认过滤、契约版本识别、旧库初始化与升级，再定稿实施。

## 与数据库向导的关系

拟由 [BL-018 setup](database-setup.md) 帮助管理员按本章权限契约设置账号，并以 writer/reader 分别验证。账号创建/GRANT 仍是管理员操作，init-db 自身不增加账号管理职责。setup 仅在用户确认计划后编排；手工 SQL 路径保留，本章的只读约束不因向导方便而放宽。
