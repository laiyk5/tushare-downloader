# CLI 交互 Demo

**对应设计：v0.2.0-draft.2**。这是使用模拟数据的视觉原型，不是下载器的实际执行画面。
行为规范以 [CLI 体验设计](cli-experience.md) 为准；原型仅展示代表性状态，不覆盖所有错误与边界。

## 交互预览

可切换 Rich/plain、quiet/normal/verbose，并播放进度、查看最近日志滚动，以及无需下载、成功和部分失败结果。
页面上的模式选择器和播放按钮只是 Demo 控件，不属于 CLI。

[独立打开 Demo](assets/cli-modes-demo.html)。如果下方预览未显示，使用这个链接。

<iframe src="../assets/cli-modes-demo.html" title="CLI output modes demo" width="100%" height="820" style="border: 0;" loading="lazy" sandbox="allow-scripts"></iframe>

## GitHub、离线与分享

- GitHub Pages / 本地 Zensical：可直接使用嵌入预览或独立页面。窄屏可独立打开以获得更大的预览空间。
- GitHub 仓库 Markdown：GitHub 不执行 HTML 交互脚本，iframe 可能被移除；HTML 链接打开的是源码。下载 HTML 后用浏览器打开，或在设计合并部署后访问 Pages。
- 离线：Demo 是独立 HTML，交互不需要 Tushare、数据库、凭据或 Codex 会话。分享该文件即可；不含真实日志、Token 或本地账户信息。
- PDF、打印或禁用脚本：交互不会保留，使用下面的文字示意和正文设计；不要把交互原型作为唯一规范。

本设计分支尚未部署到 main 的 Pages 时，不应把预期网站地址当作已经可用的分享链接。
需要冻结评审版本时使用 Git 提交固定链接，或者连同设计版本分享整个设计目录。

## 静态示意

以下为普通信息量下无需下载的情况。Rich 版本用颜色和面板组织相同内容；plain 按行呈现。

```text
Log: logs/<run>.jsonl

Nothing to download
API: stock_basic | fetch
Scope: full snapshot
Local rows: 5,911 active; 0 stale
Blocks: 0 planned; 1 skipped
Reason: existing successful fetch record satisfies the skip policy
Remote check: not performed. No rows written.

Reports: reports/<run>/{before,after}.md
```

quiet 保留启动日志路径、一行结果及报告位置；verbose 增加请求、等待和诊断上下文。
完整规则、异常处理和统计口径见 [CLI 体验设计](cli-experience.md)。

## 维护约定

Demo 随设计进入 Git，不能引用开发者电脑上的 file:// 路径或临时服务器。
修改时同步检查六种模式、播放完成状态、独立打开和静态后备说明。
它是浏览器模拟，并未调用 Python Rich；最终终端布局仍需在真实终端验收。
