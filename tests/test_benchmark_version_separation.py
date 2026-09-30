from src.benchmarks.benchmark_v1 import CAMPAIGN as V1
from src.benchmarks.benchmark_v2 import CAMPAIGN as V2
from src.benchmarks.comparison.build_comparison import build_summary


def test_campaigns_are_explicitly_separated():
    assert V1["id"] == "benchmark_v1"
    assert V2["id"] == "benchmark_v2"
    assert V1["result_root"] != V2["result_root"]
    assert set(V1["architectures"]) == {"baseline", "semantic"}
    assert set(V2["architectures"]) == {"A0", "A1", "A2", "A3"}


def test_comparison_does_not_merge_incompatible_metrics():
    summary = build_summary()
    quality = summary["directly_comparable_nominal_entity_quality"]
    assert quality["benchmark_v1_baseline"]["f1_score"] == 0.978558
    assert quality["benchmark_v2_A2"]["f1_score"] == 0.978558
    assert summary["comparison_limits"]
