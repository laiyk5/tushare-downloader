# CLI 体验设计

**设计版本：v0.2.0-draft.1**

## 命令契约

程序名称仍为 `tushare-downloader`。保留现有别名及参数位置；高频 -q/-v、一次性 --plain 保留。
长期 log-level/progress 偏好进入配置，不为翻译和排版增加选项。
stdout/stderr 优先服务人类阅读；JSONL 文件提供机器记录，不增加 --json、--no-color 等平行模式。

| 用户意图 | 命令示例 |
| --- | --- |
| 尽力补取范围 | `tushare-downloader fetch daily_basic -s 2026-09-01 -e 2026-09-10` |
| 重拉不够新的历史 | `tushare-downloader refresh daily_basic -s 2026-09-01 -e 2026-09-10 --max-age 24h` |
| 强制核对全部日期 | `tushare-downloader refresh daily_basic -s 2026-09-01 -e 2026-09-10 --max-age 0 --ignore-calendar` |
| 更新已有日频数据 | `tushare-downloader update daily_basic` |
| 对齐完整快照 | `tushare-downloader update stock_basic` |
| 预览 | 在下载命令后添加 `--dry-run` |

以上 --ignore-calendar 为拟新增选项；此页不是当前软件使用指南。
在三个下载命令上统一接受此选项；不适用接口无需额外报错，但不改变其行为。

## 帮助页

英文主帮助依次展示一句用途、Usage、按目的分组的命令、全局选项、简短示例和参考文档链接。
组为 Download（fetch/f、refresh、update/u）、Database（init-db/init、clean）、Inspect（list/ls）。
子命令帮助说明参数、默认值来源、限制及一至两个可运行示例；清理帮助保持确认要求醒目。
全局选项示例放在子命令之前，例如 `tushare-downloader --plain fetch ...`。
帮助展示静态默认规则，不加载 Token、不连接数据库、不请求日历或网络。
参数错误提供英文原因、相关 Usage 和 --help 入口；不打印完整环境变量或连接串。

## 语言与布局

程序自有提示、确认、错误、进度、报告、日志消息统一英文；原始数据值不翻译。
外部 API 的原始错误可能为中文：以英文上下文说明，保留必要原文作诊断，不把原文遗漏误认为翻译缺陷。
JSONL 现有事件名和字段保持稳定；新增日历字段遵守[统计定义](request-planning.md)。

终端使用稳定顺序：Log location → Plan → Progress → Result → Reports。stdout 输出日志位置、计划和最终摘要；stderr 输出进度及警告错误。
日志文件创建成功并写入启动事件后，立即打印并刷新 `Log: <path>`，早于本地数据库检查、日历准备和下载请求，让用户能在执行过程中监看日志。
日志位置使用可直接访问的完整路径，或明确标注相对当前工作目录；不要用省略号截断路径。此行保留在滚动历史中，不放入会刷新的 Live 区域。
quiet/plain 及重定向模式同样在启动时给出日志位置；正常结束不重复打印。结束时集中展示 before/after 报告路径。
日志初始化失败则明确报错，不展示不存在的日志文件位置。已有日志写入及时刷新的要求保留，便于 `tail -f <path>` 监看。
默认摘要限制列表长度，完整报告路径始终给出。将休市日期和连续失败日期合并为区间展示；完整报告仍能定位到块和日期。
安静模式减少成功内容，但保留错误、部分失败结果和报告位置；verbose 提供块详情，不输出密钥。

布局示意（计数示例，非运行结果）：

```text
Plan: daily_basic | fetch
Range: 2026-09-01 .. 2026-09-10
Blocks: 10 total | 2 cached | 2 calendar-filtered | 6 planned

Result: completed with failures
Blocks: 4 successful | 1 empty | 1 failed
Success: 5/6 (83.3%) including empty responses
Reports: reports/<run>/before.md, reports/<run>/after.md
```

成功率分母为计划执行块数，成功包含空响应，空响应同时单列；未尝试降低成功率而非从分母抹去。
沿用原写入分类和分母定义；零分母显示 n/a。恢复 stale 的行仍单列，不能错误计作新插入。
行统计和日历请求次数另起摘要，不塞进同一行。

Rich 交互终端保留动态进度，单独显示阶段、已完成/计划块、速率、耗时和 ETA。
日历准备显示 Preparing calendar，无数据 ETA。数据执行沿用原最少样本和滑动窗口估计；重试和提交停顿时显示阶段状态，避免虚假倒计时。
--plain 不含 ANSI、回车覆盖或动态动画。重定向时同样采用静态输出，并按配置间隔输出进展，避免每个空轮询刷屏。
80/120 列正常布局，40 列使用纵向字段；长路径和错误允许换行，不截断关键信息。

## 验证

- 所有命令主/子帮助在无凭据、无数据库和禁网环境可用，示例参数能通过解析。
- 覆盖成功、空、部分失败、全跳过、中断、数据库锁冲突和配置错误，退出码与原版一致。
- 检查 40/80/120 列、Rich/plain、重定向、长 API 错误及非 ASCII 数据；plain 无控制序列。
- 进度时钟用可控时间测试样本阈值、重试暂停、零计划和日历准备，不依赖真实等待。
- 测试语义字段、计数和必要提示；仅保留少量代表性布局快照，不锁死所有空格。
- 人工检查代表截图/文本输出，完整报告不因终端摘要限制而丢失失败和空响应列表。
