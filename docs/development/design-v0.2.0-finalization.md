# v0.2.0 设计定稿记录

日期：2026-09-14。设计标签：`design-v0.2.0`，指向包含本记录的定稿提交；软件基线仍为 v0.1.0，目标软件 v0.2.0 尚待实施与验收。

## 本轮收尾

- Demo 同步 report.md；日志与初始报告路径在执行期间可见，结束再次提供报告位置。
- 四类写入统计包含非零 Reactivated，计数互斥且合计一致。
- 十个连续自然日的日频模拟显式带 --ignore-calendar，避免与默认周末过滤矛盾。
- 跨日志分片自动跟随明确排除在本版之外，进入 backlog；本版保留全部日志并在报告列出实际分片。

## 已执行的设计演示检查

| 检查 | 结果 |
| --- | --- |
| `uv run --group docs zensical build --strict` | 通过 |
| `uv run python scripts/check_cli_demo.py` | 通过；解析生成页 iframe 的真实相对地址 |
| 浏览器打开 `/tushare-downloader/design/cli-demo/` | 嵌入可见，控件与终端模拟内容正常 |
| Rich/plain × normal/quiet/verbose × running/noop/success/partial | 24 个组合通过；日志与报告路径存在，失败可见，非 quiet 成功展示 Reactivated |
| 独立 HTML 播放 | 进度推进至 Completed，50,000 = 47,500 + 1,250 + 750 + 500 |
| 390px 视口 | 文字与路径换行；实际内容宽度 375px，scrollWidth 与 clientWidth 相等，无横向溢出 |
| 恢复默认视口 | 已恢复，并检查嵌入页面截图 |

浏览器为 Codex 内置浏览器；访问本机构建产物并保留 GitHub Pages 项目子路径。嵌入控件的模式/场景切换已验证；播放按钮因自动化 iframe 坐标限制改在独立页面验证。不是所有浏览器兼容性证明，也不是正式 Pages 已部署的证据。

本记录只验收设计演示。真实 Rich 终端、API、数据库、性能及软件发布仍须按 [验收标准](../design/acceptance.md) 执行，不能沿用本记录宣称软件 v0.2.0 已通过。
