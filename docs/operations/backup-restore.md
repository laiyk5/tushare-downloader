# 备份与恢复

以下为手工运维步骤，不是下载器子命令；没有自动备份或迁移服务。
需要与服务器兼容的 PostgreSQL 客户端工具。示例使用 Bash，密码交互输入，不写进命令。
Windows 上可在安装目录使用同版本工具，按该 shell 调整路径。

## 整库备份

```bash
mkdir -p backups
pg_dump -h localhost -p 5432 -U tushare_writer -W \
  -d tushare --format=custom --file="backups/tushare-$(date +%Y%m%d-%H%M%S).dump"
```

完整备份同时包含 raw 与 meta 的一致快照。备份含实际业务数据，应放在受限路径，
不要提交仓库或站点。角色定义不包含在单库备份中，恢复前需重建所需账号与授权。

## 恢复演练

只恢复到新建专用库 `tushare_restore_check`，不要用本例覆盖正式库。
管理员先创建由 tushare_writer 拥有的演练库（psql SQL）：

```sql
CREATE DATABASE tushare_restore_check OWNER tushare_writer;
```

然后以 Bash 执行，替换备份文件名：

```bash
pg_restore -h localhost -p 5432 -U tushare_writer -W \
  --dbname=tushare_restore_check --no-owner --no-privileges \
  --exit-on-error --single-transaction backups/替换为备份文件.dump
```

示例跳过旧 owner/ACL，并以恢复账号拥有对象；之后按[权限说明](database.md)在演练库重新授权。
若备份包含不属于此账号的扩展或下游对象，由管理员按实际对象准备权限。

检查主键和列类型、active/stale 行数、meta.schema_info、meta.slices，以及样本查询结果；
以只读账号验证 SELECT 可用且写入被拒绝。恢复会保留备份中的 database_id，
执行清理时仍需同时核对真实库名。验证完成后由管理员自行决定是否保留演练库。

本页提供操作流程，不代表已经执行过正式数据恢复演练；不得用复制运行中数据目录替代 pg_dump。
