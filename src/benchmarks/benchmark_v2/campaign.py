"""Explicit registry for the second experimental campaign."""

CAMPAIGN = {
    "id": "benchmark_v2",
    "research_question": "Compare A0-A3 under structural and semantic change.",
    "architectures": {
        "A0": ["src.baseline"],
        "A1": ["src.metadata"],
        "A2": ["src.declarative"],
        "A3": ["src.semantic"],
    },
    "experiment_code": [
        "src.evaluation.s01_benchmark",
        "src.evaluation.s02_benchmark",
        "src.evaluation.s03_benchmark",
        "src.evaluation.s04_benchmark",
        "src.evaluation.s05_benchmark",
        "src.evaluation.consolidate_semantic_benchmark",
    ],
    "structural_scenarios": ["P00", "P01", "P02", "P03", "P04", "P05"],
    "semantic_scenarios": ["S01", "S02", "S03", "S04", "S05"],
    "result_root": "results/benchmark_v2",
    "image_root": "images/benchmark_v2",
}
