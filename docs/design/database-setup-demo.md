# 数据库向导 UI Demo

**v0.4.0 / revision 3 定稿。** 此浏览器原型对应 [Textual 整体 UI 设计](database-setup-ui.md)，不是 Textual 实际运行结果，也不连接数据库或写配置。

[独立打开 Demo](assets/setup-wizard-demo.html)。

<iframe src="assets/setup-wizard-demo.html" title="Database setup Textual UI prototype" width="100%" height="1000" style="border:0" loading="lazy" sandbox="allow-scripts"></iframe>

## 体验建议

1. No configuration：原位编辑 Connection，Check 后进入 Access，再 Recheck & review。Review 中可返回编辑。Apply 需输入目标库名；完成后另行确认保存。
2. Database ready：自动检查无需变更，可直接结束、新建连接，或修改参数重新检查后保存。New connection 保留旧文件并选择独立新目标。
3. Missing reader：只补访问能力，复用已有数据库和 writer。Reader verification fails：模拟完成创建后认证失败，修正模拟凭据只重试验证。
4. 鼠标直接点击字段或页面；Tab/Shift+Tab 移动，Enter 激活当前按钮，Esc 关闭弹窗，F1 或 Keys 显示帮助。复杂快捷键已从本版范围移除；输入错误端口并点击 Check，验证原位错误提示。
5. Future migration illustration 仅展示未来迁移预览，执行禁用；真实 v0.3.0 → v0.4.0 无结构迁移。

所有凭据使用模拟选择器，请勿输入真实密码。浏览器导航按钮对应 Textual 页面导航；顶部场景/宽度/重启是 Demo 控件，不属于产品。场景固定模拟服务器事实，不模拟完整对象发现、环境覆盖、所有文件冲突和权限矩阵。首次连接检查的成功也只是模拟，不代表真实无需管理凭据即可检查。

此版取消 plain 场景，headless 完整契约见 [自动化设计](database-setup-headless.md)，不以网页冒充其实现。生产向导执行中取消、未知提交结果及隐藏密码仍以设计契约为准，本 Demo 不覆盖全部故障。

## 分享与后备

独立 HTML 可离线分享，无外部依赖。Zensical 支持嵌入；GitHub Markdown 不执行脚本，需下载 HTML 或访问部署站点。本次仅本地预览，未发布。浏览器兼容不等于 Textual 在真实终端通过验收。

```text
Connection [editable fields | readiness]
    -> Access [only missing credentials / roles]
    -> Review [before -> after | configuration destination]
    -> Confirm target -> Apply -> Result
Result -> correct credential and verify / confirm configuration save
```

本次完整设计已移除脚本包导出及自定义 F2/F6/F7/F8 快捷键；未来迁移弹窗仍为解释性示意，执行禁用，不属于当前实现承诺。原型使用固定事实、模拟凭据和简化文件保存，不承担生产权限与文件并发校验。
