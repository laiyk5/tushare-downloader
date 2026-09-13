# Excel Power Query 演示

这是可选的下游读取示例，不是下载器的验收门槛，也未声明已在你的 Excel 中实测。
Excel 连接本地 PostgreSQL 数据；更新 Tushare 数据仍由下载器完成。

Microsoft 365 Excel 的 Power Query 可使用 PostgreSQL 连接器，具体入口与可用性随版本而异。
从“数据 → 获取数据 → 从数据库 → PostgreSQL 数据库”进入，填写服务器和数据库，
使用 `tushare_reader` 只读账号。缺少组件时按微软对应版本的提示安装，
不要套用 Power BI 的内置组件假设。[微软 PostgreSQL 连接器说明](https://learn.microsoft.com/en-us/power-query/connectors/postgresql)

若当前版本没有该入口，可使用 Power Query 的 ODBC 入口；驱动位数必须匹配 Excel。
[微软导入数据说明](https://support.microsoft.com/en-us/Excel/import-data-from-data-sources-power-query)

选择 raw.daily_basic，先筛选日期并排除 stale，再加载结果。以下为可选 SQL 示例：

```sql
SELECT ts_code, trade_date, close, total_mv
FROM raw.daily_basic
WHERE NOT _is_stale
  AND trade_date BETWEEN DATE '2024-01-02' AND DATE '2024-01-05'
ORDER BY trade_date, ts_code;
```

先在终端运行下载器，再在 Excel 刷新查询。Excel 刷新不会自动调用下载器或继承省流策略。
避免一次将大量历史数据全部装入工作表；可按分析需要缩小范围或加载至数据模型。
