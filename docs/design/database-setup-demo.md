# 数据库设置问答 Demo

**保留的 revision 4 交互示例（非 revision 6 迁移 Demo）。** 对应[顺序问答设计](database-setup-ui.md)，只模拟流程，不连接数据库、不创建账户、不保存实际配置，请勿输入真实密码。

[独立打开彩色问答 Demo](assets/setup-dialogue-demo.html)。

<iframe src="assets/setup-dialogue-demo.html" title="Database setup sequential dialogue prototype" width="100%" height="1000" style="border:0" loading="lazy" sandbox="allow-scripts"></iframe>

## 体验路径

1. 首次配置：逐项输入、查看计划，Edit settings 按编号修改，确认目标名后模拟执行，再单独选择保存配置。
2. 已就绪：自动检查后直接结束；无需填写 reader 密码或选择动作。
3. 缺少表和权限：只显示必要计划；连接失败允许修正或重试，不将失败视为数据库不存在。
4. 执行中断：保留已完成操作，重新检查只列剩余操作。
5. 未支持版本：说明原因，不执行。未来升级路径仅解释分流，当前 Demo 禁止执行，不演示 revision 6 的迁移计划与执行；新版规则见 [迁移契约](database-migrations.md)。
6. 蓝色阶段、紫色参数、绿色成功、橙色变更、红色错误、灰色辅助信息；去掉颜色后仍依赖明确文字。

网页按钮对应终端选项，输入框对应当前行提示。顶部场景切换/重启是演示控件，不是 CLI 参数。交互是顺序追加，不是全屏 TUI。

## 边界与分享

Demo 保留固定的模拟事实，简化 SSL、配置来源、维护库、密码重复确认、无密码认证、秘密保存 opt-in 和文件冲突。实际产品必须满足主契约，不能照搬演示里的默认 dummy password；浏览器示例也不代替真实原生终端验收。

同一问答的 plain 行为与 headless 自动化由规范定义，不新建另一套 UI。当前网页不完整演示 plain、EOF/Ctrl+C 和生产凭据验证。

独立 HTML 无外部依赖，可离线打开或分享。Zensical iframe 内可交互；GitHub Markdown 不执行 HTML，使用独立文件或文档站入口。终端追加输出可在 shell 历史中回看，网页嵌入较长时使用独立打开入口。

旧 [revision 3 Textual 原型](assets/setup-wizard-demo.html)仅为历史参考，当前正文及验收以 [设计入口](index.md)为准；定稿标签和旧验收记录不改写。
