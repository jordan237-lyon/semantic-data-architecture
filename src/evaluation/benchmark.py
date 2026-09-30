import contextlib
import csv
import io
import json
import statistics
import time
import tracemalloc
from pathlib import Path

from src.baseline.pipeline import (
    MANUAL_SCHEMA_MAPPINGS,
    MANUAL_TRANSFORMATION_RULES,
    run as run_baseline,
)
from src.semantic.pipeline import run as run_semantic


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
COMPARISON = RESULTS / "comparison"
BASELINE_EVALUATION = RESULTS / "baseline" / "baseline_evaluation.json"
SEMANTIC_EVALUATION = (
    RESULTS / "semantic" / "pipeline" / "semantic_evaluation.json"
)
CONFIDENCE_METRICS = RESULTS / "semantic" / "schema_confidence_metrics.json"

WARMUP_RUNS = 5
MEASURED_RUNS = 30


def measure_run(name, function, iteration):
    tracemalloc.start()
    cpu_started = time.process_time()
    wall_started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        function()
    wall_seconds = time.perf_counter() - wall_started
    cpu_seconds = time.process_time() - cpu_started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "pipeline": name,
        "iteration": iteration,
        "wall_time_seconds": round(wall_seconds, 9),
        "cpu_time_seconds": round(cpu_seconds, 9),
        "python_peak_memory_bytes": peak_memory,
    }


def summarize(values):
    return {
        "mean": round(statistics.mean(values), 9),
        "median": round(statistics.median(values), 9),
        "min": round(min(values), 9),
        "max": round(max(values), 9),
        "standard_deviation": round(statistics.pstdev(values), 9),
    }


def summarize_runs(runs):
    summary = {}
    for pipeline in ("baseline", "semantic"):
        selected = [row for row in runs if row["pipeline"] == pipeline]
        summary[pipeline] = {
            "wall_time_seconds": summarize(
                [row["wall_time_seconds"] for row in selected]
            ),
            "cpu_time_seconds": summarize(
                [row["cpu_time_seconds"] for row in selected]
            ),
            "python_peak_memory_bytes": summarize(
                [row["python_peak_memory_bytes"] for row in selected]
            ),
        }
    baseline_median = summary["baseline"]["wall_time_seconds"]["median"]
    semantic_median = summary["semantic"]["wall_time_seconds"]["median"]
    summary["semantic_to_baseline_wall_time_ratio"] = round(
        semantic_median / baseline_median, 6
    )
    baseline_memory = summary["baseline"]["python_peak_memory_bytes"]["median"]
    semantic_memory = summary["semantic"]["python_peak_memory_bytes"]["median"]
    summary["semantic_to_baseline_python_memory_ratio"] = round(
        semantic_memory / baseline_memory, 6
    )
    return summary


def build_quality_comparison():
    baseline = json.loads(BASELINE_EVALUATION.read_text(encoding="utf-8"))["overall"]
    semantic = json.loads(SEMANTIC_EVALUATION.read_text(encoding="utf-8"))["overall"]
    metrics = [
        "precision",
        "recall",
        "f1_score",
        "true_positives",
        "false_positives",
        "false_negatives",
    ]
    return [
        {
            "metric": metric,
            "baseline": baseline[metric],
            "semantic": semantic[metric],
            "absolute_change": round(semantic[metric] - baseline[metric], 6),
        }
        for metric in metrics
    ]


def build_effort_comparison():
    confidence = json.loads(CONFIDENCE_METRICS.read_text(encoding="utf-8"))
    return {
        "measurement_note": (
            "Les unités décrivent des artefacts ou décisions, pas des heures de travail. "
            "Le coût initial du modèle sémantique est séparé de l'effort par intégration."
        ),
        "baseline_per_integration": {
            "manual_schema_mappings": MANUAL_SCHEMA_MAPPINGS,
            "manual_transformation_rules": MANUAL_TRANSFORMATION_RULES,
        },
        "semantic_initial_architecture": {
            "concepts": 3,
            "canonical_attributes": 14,
            "relations": 2,
            "derived_attributes": 2,
            "matching_policy": 1,
        },
        "semantic_per_integration": {
            "automatic_schema_mappings": confidence["accepted_mappings"],
            "human_validations": confidence["human_interventions_required"],
            "rejected_mappings": confidence["rejected_mappings"],
            "automation_rate": confidence["automation_rate"],
        },
    }


def run_benchmark():
    runners = {
        "baseline": run_baseline,
        "semantic": lambda: run_semantic(run_evaluation=False),
    }
    for iteration in range(WARMUP_RUNS):
        order = ("baseline", "semantic") if iteration % 2 == 0 else ("semantic", "baseline")
        for name in order:
            with contextlib.redirect_stdout(io.StringIO()):
                runners[name]()

    runs = []
    for iteration in range(1, MEASURED_RUNS + 1):
        order = ("baseline", "semantic") if iteration % 2 else ("semantic", "baseline")
        for name in order:
            runs.append(measure_run(name, runners[name], iteration))

    COMPARISON.mkdir(parents=True, exist_ok=True)
    runs_path = COMPARISON / "benchmark_runs.csv"
    with runs_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(runs[0]))
        writer.writeheader()
        writer.writerows(runs)

    summary = {
        "protocol": {
            "warmup_runs_per_pipeline": WARMUP_RUNS,
            "measured_runs_per_pipeline": MEASURED_RUNS,
            "alternating_execution_order": True,
            "memory_scope": "Python allocations measured by tracemalloc",
        },
        "performance": summarize_runs(runs),
    }
    (COMPARISON / "benchmark_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    quality = build_quality_comparison()
    with (COMPARISON / "quality_comparison.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(quality[0]))
        writer.writeheader()
        writer.writerows(quality)
    (COMPARISON / "effort_comparison.json").write_text(
        json.dumps(build_effort_comparison(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Restore the canonical artifacts after the instrumented runs.
    with contextlib.redirect_stdout(io.StringIO()):
        run_baseline()
        run_semantic()

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nRaw runs: {runs_path}")


if __name__ == "__main__":
    run_benchmark()
