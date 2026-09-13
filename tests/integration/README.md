# 集成测试

使用真实 PostgreSQL 和假 API，不请求真实 Tushare。
默认 `uv run pytest` 仅执行单元测试；显式执行本目录时必须提供独立测试数据库：

```bash
TEST_DATABASE_URL='postgresql://tushare_test:本地测试密码@localhost:55432/tushare_test' \
  uv run pytest tests/integration
```

数据库名和连接用户均必须是 tushare_test；配置缺失或不匹配会失败，不回落正式库。
本目录测试会清空测试库的 raw/meta schema，因此该数据库必须专用。
CI 使用临时 PostgreSQL 服务。不要将正式库凭据放入 TEST_DATABASE_URL。
