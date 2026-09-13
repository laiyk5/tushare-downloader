# 文档开发与部署

```bash
uv sync --locked --all-groups
uv run zensical serve
uv run zensical build --strict --clean
```

设计文档统一位于 design/，版本从[设计入口](../design/index.md)查看。

## GitHub Pages

真实仓库为 [laiyk5/tushare-downloader](https://github.com/laiyk5/tushare-downloader)。
Pages Source 已设置为 GitHub Actions。docs.yml 在 PR 上只构建，main 推送成功构建后部署；
不再额外要求 PAGES_ENABLED 变量。

项目地址由 GITHUB_REPOSITORY 推导。部署使用同一次构建的产物，
并再次确认该提交仍是 main 最新提交。PR 没有部署权限。
部署回退通过 git revert 文档提交、推送 main 后重新构建完成，不直接上传未经检查的站点目录。

Checks 工作流在 Linux Python 运行单元与真实 PostgreSQL 集成测试；
本机另验证 WSL Python 连接 Windows PostgreSQL。Windows 原生 Python 不在本版验收范围。

Actions 固定 commit SHA，对应标签记在 scripts/action-refs.json。
实际 CI、Pages 子路径、资源和回退结果记录在验收记录中；本地构建成功不代替远端验证。

## 文档组织与维护

guide/ 面向日常使用，reference/ 查命令与接口，operations/ 管理数据库，
development/ 维护开发方法与验收证据，design/ 保留设计规范。
导航按这五组组织，验证记录收纳到开发组下。

新增页面描述当前可用行为，不把设计目标写成实现事实。命令或配置变化时同步用户指南和参考；
设计正文的修改需另行明确授权，并遵循其版本约定。本轮结构整理没有修改 design/ 中任何文件。
旧 benchmark.md 保留导航，避免历史链接失效。

本地严格构建成功后，再由 PR 的 docs-build 检查页面；合并主分支才部署在线站点。
