# 文档开发与部署

```bash
uv sync --locked --all-groups
uv run zensical serve
uv run zensical build --strict --clean
```

设计文档统一位于 design/，版本从 [设计入口](../design/index.md) 查看。

## GitHub Pages

工作流 docs.yml：所有 PR 构建检查；main 推送构建后部署。当前没有配置远程仓库，**尚未部署**。

首次启用：
1. 为项目设置真实 GitHub 仓库并推送 main。
2. 在仓库 Settings → Pages 将 Source 设为 GitHub Actions。
3. 将 docs-build 设为分支必需检查，并允许 github-pages 环境由 main 部署。
4. 配置仓库变量 PAGES_ENABLED=true；未开启时工作流仅构建。
5. 运行 main 的文档工作流，检查站点子路径、导航、静态资源和搜索。

项目地址由 GITHUB_REPOSITORY 推导，配置脚本生成临时的 zensical.toml 发布字段；源码不写虚构仓库地址。部署只使用同次运行通过构建的产物，PR 没有部署权限。失败回退通过 revert 文档改动再构建。

Actions 固定 commit SHA，对应标签记在 scripts/action-refs.json。调整时核验官方引用再更新，不手工猜 SHA。本地严格构建不等于已经验证 GitHub 环境权限和实际部署。
