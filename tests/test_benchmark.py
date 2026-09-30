from src.evaluation.benchmark import summarize


def test_benchmark_summary_uses_all_measurements():
    result = summarize([1.0, 2.0, 3.0])

    assert result["mean"] == 2.0
    assert result["median"] == 2.0
    assert result["min"] == 1.0
    assert result["max"] == 3.0
    assert result["standard_deviation"] > 0
