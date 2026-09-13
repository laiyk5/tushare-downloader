# CLI 参考

程序名为 `tushare-downloader`。以下选项以当前 CLI 实现为准，可随时用 `--help` 核对。

```bash
uv run tushare-downloader [全局选项] COMMAND [命令选项]
uv run tushare-downloader --help
uv run tushare-downloader refresh --help
```

## 全局选项

| 选项 | 用途 |
| --- | --- |
| -c, --env-file FILE | 指定配置文件 |
| -q, --quiet | 减少常规进度和成功摘要 |
| -v, --verbose | 分段执行详情；不可与 -q 同用 |
| --plain | 无动态进度和 ANSI 的纯文本 |
| --version | 软件版本 |
| -h, --help | 帮助 |

全局选项放在命令前。持续偏好见[配置](../guide/configuration.md)，没有终端 JSON 输出模式。

## 命令

| 命令 | 缩写 | 参数与选项 |
| --- | --- | --- |
| list | ls | 无 API 参数；列出接口和核对能力 |
| init-db | init | 初始化或校验数据库对象 |
| fetch API | f | -s/--start、-e/--end、--dry-run |
| refresh API | 无 | 同 fetch，另有 --max-age |
| update API | u | --dry-run；无日期选项 |
| clean API | 无 | --apply、--confirm-database、--confirm-database-id |

日期格式 `YYYY-MM-DD`。时间范围接口的 fetch/refresh 必须同时给开始与结束日期；
快照接口禁止日期。`--max-age` 接受带单位时长或 `0`，其他默认策略由配置提供。
API 当前仅允许 daily_basic、stock_basic。使用示例见[下载指南](../guide/downloading.md)。
`clean` 默认只预览，实际删除步骤见[数据库运维](../operations/database.md)。

## 退出码

| 值 | 含义 |
| --- | --- |
| 0 | 无执行失败；空响应仍可能需要核实 |
| 1 | 部分/全部失败、未尝试、提交未知或运行 I/O 故障 |
| 2 | 参数或配置错误 |
| 3 | 同库写实例锁冲突 |
| 130 | 用户中断 |

失败后重跑普通命令即可；没有 status、resume 或后台任务管理命令。
