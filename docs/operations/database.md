# 数据库初始化与维护

正式库为 `tushare`，下载账号为 `tushare_writer`，下游只读账号为 `tushare_reader`。
测试库/账号为 `tushare_test`，性能测试库/账号为 `tushare_bench`；各自独立。

## 首次创建

下列是管理员在 psql 中执行的 SQL/psql 命令，不是 Bash。
账号和数据库只在不存在时创建；已有配置可直接进入 init-db。

```sql
CREATE ROLE tushare_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password tushare_writer
CREATE DATABASE tushare OWNER tushare_writer;
```

在 `.env` 配置此账号后，通过 Bash 执行：

```bash
uv run tushare-downloader init-db
```

命令在一个事务内建立 `raw` 和 `meta` 对象，并输出 database_id。
重复执行会校验结构，不会自动改列、删除表或接管不兼容的同名对象。
下游 `analysis` schema 由用户自行建立，不由下载器管理。

## 下游只读权限

管理员创建只读账号后，在 tushare 库授予查询权限（SQL/psql）：

```sql
CREATE ROLE tushare_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password tushare_reader
\connect tushare
GRANT CONNECT ON DATABASE tushare TO tushare_reader;
GRANT USAGE ON SCHEMA raw TO tushare_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO tushare_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE tushare_writer IN SCHEMA raw
  GRANT SELECT ON TABLES TO tushare_reader;
```

## 查询和维护

下列 SQL 展示本地有效数据边界，不证明日期之间无缺失，也不代表云端完整率：

```sql
SELECT min(trade_date), max(trade_date), count(*)
FROM raw.daily_basic WHERE NOT _is_stale;
SELECT trade_date, count(*) FROM raw.daily_basic
WHERE NOT _is_stale GROUP BY trade_date ORDER BY trade_date;
```

指定范围的下载前检查可用 `fetch ... --dry-run`，无需新增 status 命令。
保留 PostgreSQL autovacuum；大量写入后按需要执行 `ANALYZE raw.daily_basic`，
常规维护可执行 `VACUUM (ANALYZE) raw.daily_basic`（不要置于事务内）。不自动运行 VACUUM FULL。

## 显式物理清理

```bash
uv run tushare-downloader clean daily_basic
# 仅在确认需要删除时，填入预览返回的真实身份：
uv run tushare-downloader clean daily_basic --apply \
  --confirm-database tushare --confirm-database-id '替换为预览中的UUID'
```

实际清理会清空该 API 的 raw 行及 meta.slices 记录，而非仅删除 stale 行。
库名和 database_id 必须都匹配；下游外键阻止删除时整体失败，不级联删除。
需要保留数据时先做[备份](backup-restore.md)。
