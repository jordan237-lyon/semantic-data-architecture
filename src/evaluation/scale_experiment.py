"""Benchmark baseline and semantic pipelines at reproducible data scales."""

import contextlib
import csv
import io
import json
import shutil
import statistics
import time
import tracemalloc
from pathlib import Path

import pandas as pd

from src.baseline.pipeline import run as run_baseline
from src.evaluation.evaluate_baseline import evaluate_entity_rows, read_csv
from src.semantic.pipeline import run as run_semantic


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
TRUTH = ROOT / "data" / "ground_truth"
DATA_ROOT = ROOT / "data" / "scale"
RESULTS = ROOT / "results" / "scale"
SCALE_FACTORS = (1, 5, 10)
WARMUP_RUNS = 1
MEASURED_RUNS = 5


def _suffix_email(value, replica):
    if pd.isna(value) or replica == 0:
        return value
    local, domain = str(value).split("@", 1)
    return f"{local}.scale{replica}@{domain}"


def _replicate(frame, factor, id_columns, email_column=None):
    replicas = []
    for replica in range(factor):
        current = frame.copy()
        if replica:
            for column in id_columns:
                current[column] = current[column].apply(
                    lambda value: f"{value}-S{replica}" if pd.notna(value) else value
                )
        if email_column:
            current[email_column] = current[email_column].apply(
                lambda value: _suffix_email(value, replica)
            )
        replicas.append(current)
    return pd.concat(replicas, ignore_index=True)


def generate_scale_dataset(factor, raw_source=RAW, truth_source=TRUTH, data_root=DATA_ROOT):
    raw_source, truth_source, data_root = map(Path, (raw_source, truth_source, data_root))
    destination = data_root / f"x{factor}"
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    specs = {
        "crm": (["client_id"], "email"),
        "support": (["ticket_id", "customer_ref"], "mail"),
        "finance": (["transaction_id", "account_id"], "contact_email"),
    }
    row_counts = {}
    for source, (identifiers, email) in specs.items():
        scaled = _replicate(
            pd.read_csv(raw_source / f"{source}.csv"), factor, identifiers, email
        )
        scaled.to_csv(raw_dir / f"{source}.csv", index=False)
        row_counts[source] = int(len(scaled))

    truth = _replicate(
        pd.read_csv(truth_source / "entity_mapping.csv"),
        factor,
        [
            "canonical_customer_id", "crm_client_id",
            "support_customer_ref", "finance_account_id",
        ],
    )
    truth.to_csv(truth_dir / "entity_mapping.csv", index=False)
    shutil.copy2(truth_source / "schema_mapping.csv", truth_dir / "schema_mapping.csv")
    return destination, row_counts


def _measure(function):
    tracemalloc.start()
    started = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        function()
    wall = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return wall, peak


def _quality(output_path, truth_path):
    evaluation, _ = evaluate_entity_rows(read_csv(truth_path), read_csv(output_path))
    return evaluation["overall"]


def run_scale_experiment():
    runs, summaries = [], []
    for factor in SCALE_FACTORS:
        dataset, counts = generate_scale_dataset(factor)
        raw_dir = dataset / "raw"
        truth_path = dataset / "ground_truth" / "entity_mapping.csv"
        scenario_results = RESULTS / f"x{factor}"
        output_dir = dataset / "output"
        baseline_output = output_dir / "baseline" / "unified_customer_baseline.csv"
        semantic_output = output_dir / "unified_customer_semantic.csv"
        runners = {
            "baseline": lambda: run_baseline(
                raw_dir=raw_dir, output_dir=output_dir / "baseline",
                results_dir=scenario_results / "baseline",
            ),
            "semantic": lambda: run_semantic(
                run_evaluation=False, raw_dir=raw_dir, output_path=semantic_output,
                results_dir=scenario_results / "semantic",
                ground_truth_path=truth_path,
            ),
        }
        for function in runners.values():
            for _ in range(WARMUP_RUNS):
                _measure(function)
        for iteration in range(1, MEASURED_RUNS + 1):
            order = ("baseline", "semantic") if iteration % 2 else ("semantic", "baseline")
            for pipeline in order:
                wall, peak = _measure(runners[pipeline])
                runs.append({
                    "scale_factor": factor, "pipeline": pipeline, "iteration": iteration,
                    "wall_time_seconds": round(wall, 9),
                    "python_peak_memory_bytes": peak,
                })

        with contextlib.redirect_stdout(io.StringIO()):
            runners["baseline"]()
            run_semantic(
                raw_dir=raw_dir, output_path=semantic_output,
                results_dir=scenario_results / "semantic", ground_truth_path=truth_path,
            )
        for pipeline, output in (
            ("baseline", baseline_output), ("semantic", semantic_output)
        ):
            selected = [
                row for row in runs
                if row["scale_factor"] == factor and row["pipeline"] == pipeline
            ]
            quality = _quality(output, truth_path)
            summaries.append({
                "scale_factor": factor, "pipeline": pipeline,
                "input_rows": sum(counts.values()),
                "output_rows": len(pd.read_csv(output)),
                "median_wall_time_seconds": round(statistics.median(
                    row["wall_time_seconds"] for row in selected
                ), 9),
                "median_python_peak_memory_bytes": round(statistics.median(
                    row["python_peak_memory_bytes"] for row in selected
                )),
                "precision": quality["precision"], "recall": quality["recall"],
                "f1_score": quality["f1_score"],
            })

    RESULTS.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("benchmark_runs.csv", runs), ("scale_summary.csv", summaries)):
        with (RESULTS / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    report = {
        "phase": "after_baseline_null_fix",
        "baseline_adaptation": {
            "type": "non_comparable_missing_email_join_keys",
            "rules_added": 1,
            "manual_transformation_rules_total": 12,
        },
        "protocol": {
            "scale_factors": list(SCALE_FACTORS),
            "warmup_runs_per_pipeline_and_scale": WARMUP_RUNS,
            "measured_runs_per_pipeline_and_scale": MEASURED_RUNS,
            "memory_scope": "Python allocations measured by tracemalloc",
        },
        "results": summaries,
    }
    (RESULTS / "scale_results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    run_scale_experiment()
