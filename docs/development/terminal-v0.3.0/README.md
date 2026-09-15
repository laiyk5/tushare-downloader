# v0.3.0 真实 PTY 检查

当前 CLI 在 Linux PTY 中实际执行 --help、list、refresh --help；每项分别以 40/80/120 列、Rich/plain 两种格式运行，共 18 组。执行 cwd 为不含 .env 的临时目录，移除 Token/PG 环境变量，终端为 xterm-256color。

每组 .ansi 是原始 PTY 输出，.txt 是 pyte 解码后的屏幕字符，.png 是 Pillow/DejaVu Sans Mono 对这些字符的渲染。它们不是浏览器截图，也不代表原生终端字体逐像素一致；子进程确实连接 PTY，没有用假 isatty 替代实际运行。

summary.json 记录软件 SHA、宽度和退出码。全部退出 0，plain 输出不含 ANSI。
人工查看 help-40-rich、list-40-rich、refresh-help-40-rich、help-120-plain：标题、参数及示例可读，无丢字或重叠；40 列列表自然折行较多。

检查发现并修复了 --plain --help 的 eager 回调顺序错误：--plain 现在先于帮助处理，测试覆盖真实回调路径。修复提交 d46b49d，修复后重新捕获全部 18 组，完整单元/集成回归 233 passed。

本证据覆盖静态帮助与接口列表。动态进度在低高度/恶意文本下的当前截图和网页 Demo 的浏览器渲染仍需单独验收，不能由静态截图替代。
