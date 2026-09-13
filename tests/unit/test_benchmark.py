import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "benchmark", Path(__file__).parents[2] / "benchmarks" / "run.py"
)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_summary_retains_real_run_count_and_mad():
    result = benchmark.summarize([{"scenario": "a", "wall_seconds": v} for v in [1, 2, 3, 4, 20]])
    assert result == [
        {
            "scenario": "a",
            "runs": 5,
            "median_seconds": 3,
            "min_seconds": 1,
            "max_seconds": 20,
            "mad_seconds": 1,
        }
    ]


def test_planner_scenarios_have_expected_work():
    assert benchmark.decision_operation("skip_all", 10)()["planned_requests"] == 0
    assert benchmark.decision_operation("middle_failed", 10)()["planned_requests"] == 1
    assert benchmark.decision_operation("partial_expired", 10)()["planned_requests"] == 5
    assert benchmark.decision_operation("update_window", 10)()["planned_requests"] == 10


def test_fake_http_exercises_real_parser_and_dedup():
    result = benchmark.transport_operation(benchmark.payload(10, duplicate=True))()
    assert (result["input_rows"], result["unique_rows"], result["duplicate_rows"]) == (11, 10, 1)
    assert result["http_attempts"] == 1 and result["response_bytes"] > 0
