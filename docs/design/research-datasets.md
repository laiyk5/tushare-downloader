# A 股日频数据与框架验证

版本与状态见 [设计入口](index.md)。本版先验证现有下载框架能否以少量明确的 API 定义扩展，不把“基本支持量化研究”解释为完整回测数据库。

## 1. 范围与研究用途

保留 stock_basic、daily_basic，计划新增 daily、adj_factor、stk_limit、suspend_d。ETF、分钟数据、财务、指数行情与历史成分、历史 ST/行业归属暂留 backlog；trade_cal 继续作为既有日历依赖，不在本轮新增为用户下载表。

| 研究准备用途 | API | 本版边界 |
| --- | --- | --- |
| 证券标识及当前状态 | stock_basic | 既有快照；不是任意历史时点的股票池 |
| 估值、规模、换手等日频字段 | daily_basic | 既有只增型数据，允许主动修正 |
| 原始日线行情 | daily | 下游计算收益，下载器不做复权 |
| 复权所需原始因子 | adj_factor | 原值落盘，不合成前/后复权价格 |
| 每日涨跌停价格参考 | stk_limit | 不是成交可行性保证 |
| 停复牌事件 | suspend_d | 事件记录，不直接生成完整可交易性标签 |

组合可以服务 A 股日频行情、估值和交易约束的数据准备；缺少历史股票池、历史风险警示和其他时点资料，不能宣称已消除前视或幸存者偏差。下载成功不代表源端历史完整。

## 2. 新增 API 契约草案

共同规则：一个 API 对应 raw 下同名表；固定声明字段，文本保留代码、日期用 date、数值用 numeric/Decimal。三个价格/因子接口拟用 (ts_code, trade_date) 为非空唯一键，其他字段可空；实际字段兼容性与键冲突须在定稿前验证。

| API | 首批固定字段 | 键与日常分类 |
| --- | --- | --- |
| daily | ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount | (ts_code, trade_date)；append-only / time-range |
| adj_factor | ts_code, trade_date, adj_factor | (ts_code, trade_date)；append-only / time-range |
| stk_limit | ts_code, trade_date, pre_close, up_limit, down_limit | (ts_code, trade_date)；append-only / time-range |
| suspend_d | ts_code, trade_date, suspend_timing, suspend_type | append-only / time-range；事件唯一键待验证，不能直接假定一天一只股票只有一条 |

以 trade_date 请求全市场一天，沿用一天一块和默认至上海时区昨日的保守终点，不增加按证券代码筛选选项或证券列表循环。源 API 返回的范围原样保存，不根据当前 stock_basic 静默丢弃退市股票或其他返回行；“A 股研究范围”不等于每个源接口仅返回 A 股。

官方协议依据（2026-09-15 查阅）：[daily](https://tushare.pro/document/2?doc_id=27)、[adj_factor](https://tushare.pro/document/2?doc_id=28)、[stk_limit](https://tushare.pro/document/2?doc_id=183)、[suspend_d](https://tushare.pro/document/2?doc_id=214)。积分、频率、上限和字段能力在定稿前逐项记入契约验证记录；不能把某个账号的权限当作所有用户的保证。

## 3. 命令、请求与空数据

四个新增接口沿用总体设计的 fetch / refresh / update 规则。fetch 查缺；refresh 按核对年龄重拉，--max-age 0 强制；update 回看至默认终点并 upsert，保留未返回旧键。低频源端修正不改变只增型分类。

默认 basic 交易日过滤；calendar 与 --ignore-calendar 保留既有语义，不自动回退。不把过滤日期记为请求成功。按交易日期描述事件的 suspend_d 也暂按交易日接口设计，须在契约验证中核对；不能擅自把公告日等同交易日。

正常空响应仍作为 empty 记录与统计，沿用空响应复查间隔，不作为非空已取得或失败。suspend_d 的空响应可代表无事件，报告应提供这一解释，但不宣称证明当天没有停复牌；其他接口的空响应保留核查提示。首次 update 无本地 active 日期仍要求先 fetch；事件稀疏导致回看更长暂接受，不新设成功游标。

API 显式报错必须按既有规则分类、有限重试或失败。无显式错误的合法响应按成功处理，不仅因达到行数上限自动失败或递归分块。不过定稿必须确认“一天全市场”是受支持的请求方式及其局限；若已知接口限制无法支持它，先调整并评审请求契约，不能假装限制造成的遗漏不存在。

refresh 的缺失标 stale 继续受既有完整核对能力门槛控制。新增接口未验证该能力前不得启用；返回行的更新不依赖 stale 能力。

## 4. 最小架构调整

先尝试仅添加 API 定义与注册；规划、HTTP、去重、存储、报告继续共用。检查并替换把 daily_basic 名称硬编码为所有日频接口的分支，但不为尚未纳入的财务/指数参数设计通用 DSL、插件或多维 scope 系统。

必要差异放在 ApiSpec 的少量明确属性或小型适配函数中：字段和键、日历适用性、空响应解释、已验证的核对能力。不要在 CLI、日志和数据库各自维护一份 API 名单。

现有 (api, block_id) 检查记录对本轮每 API 固定全市场请求仍适用。以后允许 ts_code 等缩小范围时必须重新设计请求身份；本版不提前扩展此维度。suspend_d 若需要可空复合事件键，不将 NULL 转为空串或任意取第一行；先完成键证据与方案再实施。

## 5. 初始化与升级

数据库名、raw/meta schema 以及原有两张表沿用 v0.2.0。init-db 应能够在已识别且兼容的 v0.2.0 数据库中增加四张表和必要注册信息；重复执行无副作用。新增操作使用事务，失败不留下半注册状态，不删除原有行、覆盖记录或数据库身份。

不存在的新增表可以创建；同名但不兼容的表必须明确报错。正常下载遇到未初始化的新表应提示 init-db，不在请求中暗自做迁移。若实现确需调整元数据结构，须补充显式版本迁移与回滚设计后定稿，不直接重建用户库。

## 6. 代表性使用流程（目标行为）

以下是草案目标命令，不表示当前 v0.2.0 已支持这些 API。

```bash
tushare-downloader init-db
tushare-downloader f stock_basic
for api in daily_basic daily adj_factor stk_limit suspend_d; do
  tushare-downloader f "$api" -s 2026-08-03 -e 2026-08-14 || break
done
tushare-downloader u daily
tushare-downloader refresh adj_factor -s 2026-08-03 -e 2026-08-14 --max-age 0
```

每次命令独立运行、报告、提交；没有多 API 原子提交或任务管理。下游自行通过 ts_code / trade_date 关联，按原始单位解释字段。

## 7. 定稿前要补齐的证据

1. 四个 API 的权限、请求字段、单日参数、实际响应类型、历史可得范围与行数限制；不下载大规模历史来证明契约。
2. suspend_d 同日多事件、suspend_timing 为空与变化的样本，确认稳定唯一键；不能用全字段哈希掩盖身份问题。
3. 四个接口的核对范围与 stale 启用依据；没有依据时明确 refresh 仅 upsert 的限制。
4. 用真实 v0.2.0 schema 副本确认增表路径，记录所需最小元数据变化。

上述未决项解决前，本稿可讨论但不标记为可直接实施的定稿；若某接口契约不能成立，应明确修订范围，不悄悄跳过其验收。
