# Benchmark

```bash
uv run python benchmarks/run.py --mode cpu --rows 1000 --repeat 5
```

Separate cpu, database and api modes retain all samples and summarize medians and variability, with at least five repetitions.
Database mode requires the dedicated tushare_bench database and role. Real API mode never writes to a database.
See the [guide](../docs/development/benchmarks.md) for the complete flow benchmark and measurement boundaries.
results/ is ignored by Git. Historical measurements in docs/development/ remain evidence for their recorded versions only.
