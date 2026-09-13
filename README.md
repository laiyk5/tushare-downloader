# tushare-downloader

Tushare Pro → PostgreSQL 下载工具，目前仅完成项目骨架，**下载、配置加载与数据库功能尚未实现**。

- [设计入口](docs/design/index.md)
- [开发环境](docs/development/setup.md)
- [文档部署](docs/development/documentation.md)

## 本地开始（Bash / WSL）

```bash
cd /home/laiyk/projects/tools/tushare-downloader
uv sync --locked --all-groups
uv run pre-commit install
uv run tushare-downloader --help
uv run pytest
uv run zensical serve
```

当前只有占位说明、帮助和版本入口。设计中的 fetch/refresh/update 是实现目标，尚不能运行。

Python 版本见 .python-version，工具及依赖通过 uv.lock 固定。可编辑本地 .env 填写未来所需 Token/数据库参数；当前入口不会读取它或连接数据库。

原 Windows 工作目录的设计已迁入本仓库，后续以本仓库 docs/design 为唯一维护源。软件包版本 0.1.0 是初始元数据，不表示已正式发布或完成设计验收。
