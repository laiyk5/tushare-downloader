# 开发环境

## 已配置

使用 WSL Ubuntu 中的项目与独立 .venv。Python 3.12.3，uv 0.12.10；生产依赖包含 requests、psycopg、dotenv、Click、Rich、tzdata；开发工具为 Ruff、pytest、pytest-cov、pre-commit，文档为 Zensical。

```bash
uv sync --locked --all-groups
uv run pre-commit install
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=tushare_downloader --cov-branch
uv build
uv run tushare-downloader --help
```

当前仅有 CLI/打包冒烟测试，不存在下载或数据库集成测试。tests/integration 和 benchmarks 先保留说明，随实现补充。

## 本地配置

.env.example 只含占位值。首次准备时复制为 .env，填入自己的配置；当前没有配置加载逻辑。不要将 Token 或密码放入命令参数、Git 或报告。

PostgreSQL 仍可使用 Windows 上的服务，无需在 WSL 再装一套。PGHOST=localhost 只是示例：WSL 网络模式、服务器监听与认证配置决定实际可达地址。连接在实现数据库功能前另行验证；本次未修改 PostgreSQL、Windows 防火墙或真实数据。

## 代码边界

cli.py 只提供占位提示、--help 和 --version；其他模块仅有用途说明。保留原有 apis/ 包作为 API 定义位置；download.py 承接未来执行流程。不实现假成功的下载命令。

## 检查工作流

ci.yml 在 Ubuntu 与 Windows 运行静态检查、基础 pytest、wheel 构建和隔离安装验证；目前不连数据库或 API。pre-commit 的本地 Ruff hook 由 uv.lock 固定版本。当前文件未提交时可先运行 Ruff；pre-commit --all-files 仅检查 Git 已跟踪文件。
