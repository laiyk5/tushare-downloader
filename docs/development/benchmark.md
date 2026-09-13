# Benchmark 使用方法

分层测量，不把网络等待、本地解析和数据库写入混成一个速度。
入口是开发脚本 `benchmarks/run.py`，不增加下载器的日常 CLI 选项。

## 本地处理与展示

```bash
uv run python benchmarks/run.py --mode cpu --rows 1000 --repeat 5
```

无需 Token 或数据库。使用真实客户端解析逻辑和假 HTTP 响应，关闭网络与限速等待。
覆盖普通/重复行解析、首次补齐/全跳过/中间失败/部分过期/强制核对/更新窗口/空响应的请求选择，
1/7/30 天块大小的请求数和夹带天数，以及 plain、进度关闭、DEBUG、Rich 展示。

规划场景只测纯函数；块大小实验不是改变 daily_basic 的实际一天一请求协议。
展示基准使用内存终端（Rich 为模拟 TTY）和真实文件输出，不能等同于真实终端绘制性能。

## PostgreSQL 写入

```bash
BENCH_DATABASE_URL='postgresql://tushare_bench:测试密码@localhost:55432/tushare_bench' \
  uv run python benchmarks/run.py --mode database --rows 1000 --repeat 5
```

数据库与用户必须都是 tushare_bench；缺失配置会报错，不读取正式库连接。
该库必须专用：每轮清理测试数据并准备固定输入，准备时间不计入测量；
计时覆盖真实 COPY、合并、元数据写入和 COMMIT。
覆盖新增、未变、字段更新、stale、恢复、空响应。
未变场景仍更新 _last_seen_at，不能理解为零写入。
这里的临时 55432 地址只是示例，不保证当前有服务运行。

## 少量真实 API

```bash
uv run python benchmarks/run.py --mode api --date 2024-01-02 --repeat 5
```

使用本地配置中的 Token，仅请求 daily_basic 指定日期，不连接或写入数据库。
此模式保留实际限速和重试，会消耗接口请求额度；默认至少运行五次。
接口权限不足或请求失败时明确失败，不用假数据代替。

## 结果与指标

输出到 benchmarks/results/UTC时间-随机标识/，默认不提交：

- samples.jsonl：保留每次原始样本与场景指标。
- environment.json：Python/依赖/平台/CPU 数量和 PostgreSQL 版本（数据库模式）。
- summary.json、summary.md：每个场景的次数、中位数、最小/最大值和 MAD（中位绝对偏差）。

指标包括墙钟时间、Python 分配内存峰值、HTTP 尝试、实际读取的响应体字节数，
HTTP/解析/限速/重试计时，以及对应的请求选择、去重、写入或展示统计。
HTTP 时间包括连接及读取响应体；字节数为 requests 解码后的响应体，不含 HTTP 头。
数据库准备与样本输入生成在计时之外，所有测量启用 tracemalloc，有额外开销。
Python 内存峰值不包含 PostgreSQL 服务、操作系统缓存或完整进程 RSS。

各层数据规模和边界不同，不能将中位数直接相加推算端到端耗时，也不设跨机器固定 CI 性能门槛。
真实下载的 invocation_finished 日志另有检查/计划、入库、报告、日志及客户端各阶段耗时；
这些是阶段观测，整体耗时以单独墙钟测量为准。

本次本机结果见[基准记录](benchmark-baseline.md)。性能数值只描述该环境和固定样本。

终端与文件报告的示例见[报告样例](output-examples.md)。

## 完整执行流程

```bash
BENCH_DATABASE_URL='postgresql://tushare_bench:测试密码@localhost:55432/tushare_bench' \
  uv run python benchmarks/flow.py --rows 100 --repeat 5
```

此脚本运行真正的执行器、请求解析、PostgreSQL 写入和日志/报告。
HTTP 来源为固定假响应，网络和限速等待关闭且明确记录；源响应与数据库准备在计时之外。
场景覆盖首次补齐、全部跳过、中间失败补齐、部分过期、全刷新、追增、删除/恢复、
空响应、重复键、部分请求失败和长报告；每场景至少五次。
数据库及账号必须为 tushare_bench，绝不回落正式库。
