"""Benchmark the unchanged A2 pipeline at scales x1, x5 and x10."""

import csv
import io
import json
import statistics
from contextlib import redirect_stdout
from pathlib import Path

from src.declarative.pipeline import run as run_a2

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "benchmark_v2" / "P04" / "A2"
OUTPUTS = ROOT / "data" / "output" / "benchmark_v2" / "P04" / "A2"
SCALES = ("x1", "x5", "x10")
REPETITIONS = 5


def run_scale(scale):
    data_root = ROOT / "data" / "scale" / scale
    result_dir = RESULTS / scale
    output_path = OUTPUTS / scale / "unified_customer_a2.csv"
    durations = []
    metrics = None
    for _ in range(REPETITIONS):
        with redirect_stdout(io.StringIO()):
            metrics = run_a2(
                raw_dir=data_root / "raw",
                output_path=output_path,
                results_dir=result_dir,
                ground_truth_path=data_root / "ground_truth/entity_mapping.csv",
            )
        durations.append(metrics["execution_time_seconds"])
    metrics["benchmark_repetitions"] = REPETITIONS
    metrics["execution_time_seconds_runs"] = durations
    metrics["execution_time_seconds_median"] = round(statistics.median(durations), 6)
    (result_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "scale": scale,
        "benchmark_repetitions": REPETITIONS,
        "output_rows": metrics["output_rows"],
        "precision": metrics["entity_quality"]["precision"],
        "recall": metrics["entity_quality"]["recall"],
        "f1_score": metrics["entity_quality"]["f1_score"],
        "median_seconds": metrics["execution_time_seconds_median"],
        "declarative_adaptations": 0,
    }


def run():
    rows = [run_scale(scale) for scale in SCALES]
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "scale_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS / "scale_summary.json").write_text(
        json.dumps({"architecture": "A2", "results": rows}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return rows


if __name__ == "__main__":
    run()
