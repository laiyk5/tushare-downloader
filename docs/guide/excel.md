# Excel Power Query example

Use Excel to read downloaded PostgreSQL data for analysis. Run the downloader to
update the database, then refresh the query in Excel. Refreshing Excel does not
run the downloader or apply its request-skipping rules.

## Connect to PostgreSQL

In Microsoft 365 Excel, look for **Data → Get Data → From Database → From
PostgreSQL Database**. Connector availability depends on your Excel version.
Enter the server and database, and connect with the read-only `tushare_reader`
account described in [database administration](../operations/database.md).

If Excel asks for a component, follow the instructions for your version. Power BI's
bundled components do not establish what Excel has installed. See Microsoft's
[PostgreSQL connector documentation](https://learn.microsoft.com/en-us/power-query/connectors/postgresql).

If the PostgreSQL entry is unavailable, use Power Query's ODBC entry with a
PostgreSQL ODBC driver matching Excel's bitness. See Microsoft's
[data import instructions](https://support.microsoft.com/en-us/Excel/import-data-from-data-sources-power-query).

## Load a limited range

Select `raw.daily_basic`, filter the dates and exclude stale rows before loading.
You can also use this SQL query:

```sql
SELECT ts_code, trade_date, close, total_mv
FROM raw.daily_basic
WHERE NOT _is_stale
  AND trade_date BETWEEN DATE '2024-01-02' AND DATE '2024-01-05'
ORDER BY trade_date, ts_code;
```

Keep worksheet loads within the range needed for your analysis; consider the data
model for larger results. This is an optional downstream example, not a downloader
acceptance requirement or a claim that your Excel installation has been tested.
