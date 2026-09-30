"""Explicit registry for the first experimental campaign.

The implementation remains in its original modules to preserve reproducibility.
This registry provides one unambiguous entry point without duplicating engines.
"""

CAMPAIGN = {
    "id": "benchmark_v1",
    "research_question": "Compare a manual ETL baseline with a semantic-assisted pipeline.",
    "architectures": {
        "baseline": ["src.baseline"],
        "semantic": ["src.semantic"],
    },
    "experiment_code": [
        "src.evaluation.evaluate_baseline",
        "src.evaluation.benchmark",
        "src.evaluation.perturbations",
        "src.evaluation.perturbation_p02",
        "src.evaluation.perturbation_p03",
        "src.evaluation.scale_experiment",
        "src.evaluation.new_source_experiment",
        "src.evaluation.final_synthesis",
    ],
    "scenarios": ["P00", "P01", "P02", "P03", "P04", "P05"],
    "result_root": "results/benchmark_v1",
    "image_root": "images/benchmark_v1",
}
