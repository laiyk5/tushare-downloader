# 下载、核对与更新

## 按目的选择命令

| 目的 | 命令 | 本地跳过和写入行为 |
| --- | --- | --- |
| 尽力补齐指定范围 | fetch（f） | 按有效成功检查记录跳过；未覆盖或需重查的段重新请求 |
| 同步云端修正 | refresh | 核对年龄不超过 max-age 的段跳过；0 强制请求并核对 |
| 追增日频数据 | update（u）daily_basic | 从本地最新 active 日期回看至上海时区昨日，窗口内重新请求并写入 |
| 同步可变快照 | update（u）stock_basic | 拉取全部声明状态，全部成功后统一合并，缺失旧行标 stale |

有效的成功空响应按 `EMPTY_RECHECK_AGE` 判断重查，refresh 的 `--max-age 0` 可立即强制重查。
日期范围包含起止两端。`daily_basic` 通常只增，但历史也可能修正，因此保留 refresh。
`fetch` 不会仅凭某日有一行数据就认定整个日期已覆盖。

```bash
uv run tushare-downloader f daily_basic -s 2024-01-02 -e 2024-01-31
uv run tushare-downloader refresh daily_basic -s 2024-01-02 -e 2024-01-31 --max-age 0
uv run tushare-downloader u daily_basic --dry-run
uv run tushare-downloader u daily_basic
uv run tushare-downloader u stock_basic
```

空库的日频数据先用 fetch 建立起始范围，再用 update 追增；工具不猜测全历史起点。
快照不接受日期。`LOOKBACK_DAYS` 控制回看长度（含本地最新日期，例如 7 表示从该日期前 6 天起）；已有数据离现在很远时，先 dry-run 检查请求量。

## 失败和重跑

独立日期块逐段提交；某块失败不会撤销此前成功块。失败达到连续失败阈值后停止，
报告区分失败和未尝试范围。修复原因后重新执行 fetch 可补齐，不需要 resume。

快照的五个必要请求构成一个逻辑范围；其中一个失败时不合并旧表。
提交确认丢失时停止并报告“提交未知”，不能把它计作确认成功，也不能断言已回滚。
成功空响应单独标为待核实；API 没报错不等于业务完整性的证明。

## 读懂输出

stdout 为下载前后报告，stderr 为进度、警告和错误。
前报告展示本地概况、实际范围以及请求/跳过计划；后报告列出成功、空、失败、未尝试、
提交未知，以及新增、更新、未变、恢复和 stale 行数。

进度达到 100% 表示计划已处理，不表示全部成功。网络取得/暂存和确认入库分别显示。
ETA 需要至少五个完整块样本且累计十秒，使用最近最多二十块估计；
重试等待、提交等阶段可能暂时隐藏。快照暂存不计入已提交成功。

终端按分类压缩长列表；完整 `before.md`、`after.md` 位于本次 `reports/` 子目录。
强制终止可能没有 after.md；日志/报告写入故障会告警，已提交数据不会因此撤销。
布局样例见[报告样例](../development/output-examples.md)。

```bash
# 替换为终端给出的本次日志文件路径
LOG_FILE='./logs/替换为实际文件名.jsonl'
tail -n 20 -F "$LOG_FILE"
jq -c 'select(.event == "slice_result")' "$LOG_FILE"
jq -c 'select(.event == "slice_result" and .outcome == "failed")' "$LOG_FILE"
```

日志每 10 MiB 轮转，单次调用片段全部保留；完整查询需要包含该次全部轮转片段。
退出码定义见[CLI 参考](../reference/cli.md)。本地覆盖只描述数据库与检查记录，不能推算云端完整率。
