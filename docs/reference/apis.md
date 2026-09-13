# API 与数据表

| API / 数据表 | 分类 | 业务唯一键 | 请求形态 |
| --- | --- | --- | --- |
| daily_basic / raw.daily_basic | 通常只增 | ts_code, trade_date | 每天一块，按 trade_date 请求 |
| stock_basic / raw.stock_basic | 可变快照 | ts_code | L、D、P、G、UN 状态共同组成当前全集 |

接口字段使用固定声明，文本保留前导零，日期转换为 date，数值使用 Decimal/numeric，
源 null 写入 SQL NULL。字段顺序可变，但缺字段、重复字段、非法类型或行宽错误会失败。
当前字段清单见下表，实际表列也可通过 psql `\d raw.daily_basic` 查看。

daily_basic 的 update 默认结束于 Asia/Shanghai 昨日；它不是源数据永不修正的承诺。
stock_basic 只有全部必要状态请求成功且总集合非空才核对缺失键；总集合为空时保留旧行。
两者已启用缺失核对能力，范围外的行不受本次范围核对影响。

## 技术字段与检查记录

| 字段 | 含义 |
| --- | --- |
| _is_stale | 在可靠核对范围中源端已不再返回的旧行 |
| _stale_at | 标记 stale 的时间 |
| _last_seen_at | 最近一次确认返回并入库的时间 |
| _updated_at | 源字段或行状态最近变化的时间 |

默认下游分析通常筛选 `NOT _is_stale`。stale 行保留以避免破坏下游引用，重新出现可恢复。
`meta.schema_info` 保存数据库身份和受管理版本；`meta.slices` 保存分块检查事实，
不是任务队列。不要手动修改它们来“修复”跳过行为；需要重新核对时使用 refresh。

真实样本及验证边界见[实现验证](../development/verification.md)，
请求与更新操作见[下载指南](../guide/downloading.md)。当前没有任意 API 自动建表或任意参数透传。

## 源字段清单

以下由当前 ApiSpec 核对整理。业务唯一键列不可为空，其他列按接口声明允许 NULL。

### daily_basic

| 字段 | PostgreSQL 类型 | 唯一键组成 | 允许 NULL |
| --- | --- | --- | --- |
| ts_code | text | 是 | 否 |
| trade_date | date | 是 | 否 |
| close | numeric | 否 | 是 |
| turnover_rate | numeric | 否 | 是 |
| turnover_rate_f | numeric | 否 | 是 |
| volume_ratio | numeric | 否 | 是 |
| pe | numeric | 否 | 是 |
| pe_ttm | numeric | 否 | 是 |
| pb | numeric | 否 | 是 |
| ps | numeric | 否 | 是 |
| ps_ttm | numeric | 否 | 是 |
| dv_ratio | numeric | 否 | 是 |
| dv_ttm | numeric | 否 | 是 |
| total_share | numeric | 否 | 是 |
| float_share | numeric | 否 | 是 |
| free_share | numeric | 否 | 是 |
| total_mv | numeric | 否 | 是 |
| circ_mv | numeric | 否 | 是 |

### stock_basic

| 字段 | PostgreSQL 类型 | 唯一键组成 | 允许 NULL |
| --- | --- | --- | --- |
| ts_code | text | 是 | 否 |
| symbol | text | 否 | 是 |
| name | text | 否 | 是 |
| area | text | 否 | 是 |
| industry | text | 否 | 是 |
| fullname | text | 否 | 是 |
| enname | text | 否 | 是 |
| cnspell | text | 否 | 是 |
| market | text | 否 | 是 |
| exchange | text | 否 | 是 |
| curr_type | text | 否 | 是 |
| list_status | text | 否 | 是 |
| list_date | date | 否 | 是 |
| delist_date | date | 否 | 是 |
| is_hs | text | 否 | 是 |
