# 开发环境

在 WSL/Linux 中检出项目，Python 与依赖版本由 `.python-version`、`uv.lock` 固定。

```bash
uv sync --locked --all-groups
uv run pre-commit install
uv run pre-commit run --all-files
uv run zensical serve
```

Ruff 负责检查和格式化，pre-commit 不运行真实 API 或数据库重测试。
日常使用配置见[配置指南](../guide/configuration.md)，安装和首个下载见[快速开始](../guide/quickstart.md)。
测试命令见[测试方法](testing.md)，性能测量见[Benchmark](benchmarks.md)，站点发布见[文档部署](documentation.md)。

## 代码入口

| 模块 | 职责 |
| --- | --- |
| cli.py / config.py | 命令和配置 |
| apis/ | 显式 API 定义、字段与唯一键 |
| planning.py | 日期块和请求选择 |
| client.py | HTTPS、解析、限速和重试 |
| storage.py | 受管理对象、事务、合并和检查记录 |
| download.py | 自检、计划、执行与收尾 |
| reporting.py | 终端进度、Markdown 报告与 JSONL |

设计决策见[设计入口](../design/index.md)。用户指南按当前实现维护，设计正文另行版本管理；
本轮文档组织不修改设计正文。尚未完成项见[验收记录](acceptance.md)与[后续待办](backlog.md)。
