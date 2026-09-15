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

## 2. 新增 API 契约

共同规则：一个 API 对应 raw 下同名表；固定声明字段，文本保留代码、日期用 date、数值用 numeric/Decimal。四个接口使用 (ts_code, trade_date) 为非空唯一键，其他字段可空；suspend_d 的键是带运行时检查的工作假设，不宣称源端保证唯一。

| API | 首批固定字段 | 键与日常分类 |
| --- | --- | --- |
| daily | ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount | (ts_code, trade_date)；append-only / time-range |
| adj_factor | ts_code, trade_date, adj_factor | (ts_code, trade_date)；append-only / time-range |
| stk_limit | ts_code, trade_date, pre_close, up_limit, down_limit | (ts_code, trade_date)；append-only / time-range |
| suspend_d | ts_code, trade_date, suspend_timing, suspend_type | (ts_code, trade_date)；append-only / time-range；同键异值必须报错 |

以 trade_date 请求全市场一天，沿用一天一块和update 默认至上海时区昨日的保守终点，不增加按证券代码筛选选项或证券列表循环。显式 fetch/refresh 可请求上海当天的暂定数据，但不能请求未来日期；之后的 update 回看或 refresh 可再次核对，成功记录仍遵守总体设计的暂定数据复查规则。源 API 返回的范围原样保存，不根据当前 stock_basic 静默丢弃退市股票或其他返回行；“A 股研究范围”不等于每个源接口仅返回 A 股。

官方协议依据（2026-09-15 查阅）：[daily](https://tushare.pro/document/2?doc_id=27)、[adj_factor](https://tushare.pro/document/2?doc_id=28)、[stk_limit](https://tushare.pro/document/2?doc_id=183)、[suspend_d](https://tushare.pro/document/2?doc_id=214)。不能把某个账号的权限当作所有用户的保证。官方页面未给出的具体数值不自行推定；沿用配置限速和显式 API 错误处理。

| API | 官方请求与限制说明 | 本版处理 |
| --- | --- | --- |
| daily | 支持 trade_date 全市场；页面列 6000 行/次、基础积分 500 次/分钟 | 一日一块；请求固定字段，不包含可选盘后字段；配置限速不自动提高到文档上限 |
| adj_factor | 支持单日全部股票；2000 积分起、5000 以上更高频；页面未列具体行数和频次上限 | 一日一块，不将通用默认行数当官方承诺 |
| stk_limit | 支持单日全部股票；2000 积分、5800 行/次；pre_close 为非默认字段 | 显式请求 pre_close；保留接口原始证券范围 |
| suspend_d | 支持 trade_date，suspend_type 可选；2000 积分、5000 更高频；页面未列具体行数上限 | 不传 suspend_type，避免只获取 S 或 R；保留全部四个字段 |

这些页面没有承诺统一的最早历史日期，因此允许用户指定范围，源端正常空结果如实报告，不虚构历史覆盖起点。行数限制是接口说明，不是单凭返回行数就能判断完整性的规则。

## 3. 命令、请求与空数据

四个新增接口沿用总体设计的 fetch / refresh / update 规则。fetch 查缺；refresh 按核对年龄重拉，--max-age 0 强制；update 回看至默认终点并 upsert，保留未返回旧键。低频源端修正不改变只增型分类。

默认 basic 交易日过滤；calendar 与 --ignore-calendar 保留既有语义，不自动回退。不把过滤日期记为请求成功。suspend_d 按文档的 trade_date 查询并应用同一可绕过过滤器；这不是对所有历史事件日期的保证。用户需要查看被过滤日期时使用 --ignore-calendar。

正常空响应仍作为 empty 记录与统计，沿用空响应复查间隔，不作为非空已取得或失败。suspend_d 的空响应可代表无事件，报告应提供这一解释，但不宣称证明当天没有停复牌；其他接口的空响应保留核查提示。首次 update 无本地 active 日期仍要求先 fetch；事件稀疏导致回看更长暂接受，不新设成功游标。

API 显式报错必须按既有规则分类、有限重试或失败。无显式错误的合法响应按成功处理，不仅因达到行数上限自动失败或递归分块。不过定稿必须确认“一天全市场”是受支持的请求方式及其局限；若已知接口限制无法支持它，先调整并评审请求契约，不能假装限制造成的遗漏不存在。

四个新增接口的 refresh 启用请求日期范围内的 stale 核对：按 trade_date 请求、不附加证券或事件类型筛选，合法成功且非空的响应作为该日比较集合；本地同日未返回旧键标 stale。跳过、过滤、失败日期不参与；整体空响应沿用总体设计的保留旧行规则。fetch 与只增型 update 不标记未返回旧键。

这不是性能限制，也不要求证明源端绝对完整。沿用“API 未报错的合法响应视为成功”的边界，不增加隐式完整性探测。已知的筛选范围差异必须避免；源端静默漏数仍可能造成误标，后续返回同键时恢复 active。日期索引与数据库内范围反连接用于完成核对，不把整表搬到 Python。

## 4. 最小架构调整

先尝试仅添加 API 定义与注册；规划、HTTP、去重、存储、报告继续共用。检查并替换把 daily_basic 名称硬编码为所有日频接口的分支，但不为尚未纳入的财务/指数参数设计通用 DSL、插件或多维 scope 系统。

必要差异放在 ApiSpec 的少量明确属性或小型适配函数中：字段和键、日历适用性、空响应解释、已验证的核对能力。不要在 CLI、日志和数据库各自维护一份 API 名单。

现有 (api, block_id) 检查记录对本轮每 API 固定全市场请求仍适用。以后允许 ts_code 等缩小范围时必须重新设计请求身份；本版不提前扩展此维度。suspend_d 复用现有 parse_rows 检查：同一逻辑日响应内同键同值折叠计数；同键异值抛 duplicate_conflict，该日不写入、不标 stale、不登记成功，其余独立日期按既有失败规则继续。该检查使用显式异常，不使用可被优化关闭的 assert。不同请求间同键异值仍按源端修正正常 upsert。若运行中证实同日多事件是合法形态，再修订接口键和迁移设计，不能静默扩键或任取一条。

## 5. 初始化与升级

数据库名、raw/meta schema 以及原有两张表沿用 v0.2.0。init-db 应能够在已识别且兼容的 v0.2.0 数据库中增加四张表和必要注册信息；重复执行无副作用。新增操作使用事务，失败不留下半注册状态，不删除原有行、覆盖记录或数据库身份。

不存在的新增表可以创建；同名但不兼容的表必须明确报错。正常下载遇到未初始化的新表应提示 init-db，不在请求中暗自做迁移。源码核对确认：Store.initialize 已在单一事务中遍历 APIS，校验已有注册项，为未注册 API 建表、日期索引并追加 specs；本轮无需改变元数据结构或 SCHEMA_VERSION。新增 ApiSpec 使用初始 spec_version，旧接口版本不变。任何未注册的同名表都拒绝接管，即使列结构相似；异常回滚本次全部新增表与注册项。实施时补充 v0.2.0 数据库升级回归即可，不要求用户决定迁移机制。

## 6. 代表性使用流程（目标行为）

以下是 v0.3.0 目标命令，不表示当前 v0.2.0 已支持这些 API。

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

## 7. 决策与后续验证

本轮已根据官方文档和源码确定单日请求契约、受检查的唯一键、范围 stale 规则及增表路径。有限样本不能证明源端永远唯一或完整，不再将这种证明列为定稿条件。

实施阶段验证：同键同值/异值、跨请求修正、正常空结果、范围外行拒绝、失败不写、stale 范围隔离，以及真实 v0.2.0 schema 的事务增表与回滚。真实 API 冒烟验证账号权限和协议兼容性，不将未执行记录成通过。
