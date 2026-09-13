# 测试方法

测试使用等价类划分与边界值分析，有限样例不能证明所有输入正确。
单元测试不使用真实 Token 或外部数据库；事务、COPY 和提交故障使用真实 PostgreSQL。

```bash
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit --cov=tushare_downloader --cov-branch
uv build
```

默认 `uv run pytest` 只收集 tests/unit。覆盖率帮助定位未测分支，不设虚构的发布百分比门槛。

## PostgreSQL 集成测试

先创建独立 `tushare_test` 账号和同名专用数据库，账号需能管理测试对象。
测试会删除其中的 raw/meta schema；不得指向正式库。端口 55432 只是示例，临时实例不会常驻。

```bash
TEST_DATABASE_URL='postgresql://tushare_test:测试密码@localhost:55432/tushare_test' \
  uv run pytest tests/integration
```

fixture 直接读取进程环境变量，不自动加载 `.env`。数据库与用户名必须都匹配，
缺失配置明确失败。测试包含命令分类矩阵、分段事务、stale/恢复、失败后重跑、
COMMIT 前后真实断连、pg_terminate_backend、Ctrl+C、输出 I/O 故障和实例锁。

GitHub Checks 在 Ubuntu 上运行单元检查、wheel 隔离安装及 PostgreSQL 18 集成测试。
本地验证覆盖 WSL Python 连接 Windows PostgreSQL；Windows 原生 Python 不在本版验收范围。
真实 Tushare 小样本与性能结果单独记录，不将 Token 放入自动测试。

当前证据见[验收记录](acceptance.md)，协议样本见[实现验证](verification.md)，
性能方法见[Benchmark](benchmarks.md)。
