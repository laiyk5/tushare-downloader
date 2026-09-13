# Benchmark

```bash
uv run python benchmarks/run.py --mode cpu --rows 1000 --repeat 5
```

支持 cpu、database、api 三种独立测量模式，默认至少重复五次，保留每次样本及中位数/波动。
数据库模式仅允许专用 tushare_bench 库和账号；真实 API 模式不写数据库。
详见 [使用指南](../docs/development/benchmark.md)。
输出 results/ 默认不提交；人工选定的本机基准记录保存在 docs/development/benchmark-baseline.md。
