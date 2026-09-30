"""Run the unchanged A1 pipeline on perturbations P01 through P05."""

import csv
import io
import json
import statistics
from contextlib import redirect_stdout
from pathlib import Path

from src.evaluation.evaluate_baseline import extract_pairs, read_csv
from src.evaluation.metrics import evaluate_pairs
from src.metadata.pipeline import run as run_a1


ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "results" / "benchmark_v2"
OUTPUT_ROOT = ROOT / "data" / "output" / "benchmark_v2"
REPETITIONS = 5

CASES = [
    ("P01", None, ROOT / "data/perturbations/p01_renamed_column"),
    ("P02", None, ROOT / "data/perturbations/p02_country_format"),
    ("P03", None, ROOT / "data/perturbations/p03_merged_name_columns"),
    ("P04", "x1", ROOT / "data/scale/x1"),
    ("P04", "x5", ROOT / "data/scale/x5"),
    ("P04", "x10", ROOT / "data/scale/x10"),
    ("P05", None, ROOT / "data/new_source/loyalty"),
]


def loyalty_quality(truth_path, output_path):
    """Evaluate the new CRM-Loyalty relation separately from legacy relations."""
    truth = read_csv(Path(truth_path))
    predicted = read_csv(Path(output_path))
    columns = ("crm_client_id", "loyalty_member_id")
    return evaluate_pairs(
        extract_pairs(predicted, *columns),
        extract_pairs(truth, *columns),
    )


def run_case(scenario, variant, data_root):
    suffix = Path(variant) if variant else Path()
    result_dir = RESULTS_ROOT / scenario / "A1" / suffix
    output_path = OUTPUT_ROOT / scenario / suffix / "unified_customer_a1.csv"
    durations = []
    metrics = None
    for _ in range(REPETITIONS):
        with redirect_stdout(io.StringIO()):
            metrics = run_a1(
                raw_dir=data_root / "raw",
                output_path=output_path,
                results_dir=result_dir,
                ground_truth_path=data_root / "ground_truth/entity_mapping.csv",
            )
        durations.append(metrics["execution_time_seconds"])

    metrics["benchmark_repetitions"] = REPETITIONS
    metrics["execution_time_seconds_runs"] = durations
    metrics["execution_time_seconds_median"] = round(statistics.median(durations), 6)
    if scenario == "P05":
        metrics["crm_loyalty_quality"] = loyalty_quality(
            data_root / "ground_truth/entity_mapping.csv", output_path
        )
    (result_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "scenario": scenario,
        "variant": variant or "default",
        "sources": len(metrics["discovered_sources"]),
        "profiled_columns": metrics["profiled_columns"],
        "mapped_technical_roles": metrics["mapped_technical_roles"],
        "review_columns": metrics["review_columns"],
        "output_rows": metrics["output_rows"],
        "precision": metrics["entity_quality"]["precision"],
        "recall": metrics["entity_quality"]["recall"],
        "f1_score": metrics["entity_quality"]["f1_score"],
        "median_seconds": metrics["execution_time_seconds_median"],
        "crm_loyalty_f1": metrics.get("crm_loyalty_quality", {}).get("f1_score", ""),
    }


def run():
    rows = [run_case(*case) for case in CASES]
    summary_csv = RESULTS_ROOT / "a1_campaign_summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary_json = RESULTS_ROOT / "a1_campaign_summary.json"
    summary_json.write_text(
        json.dumps({"architecture": "A1", "results": rows}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    print(summary_csv)
    return rows


if __name__ == "__main__":
    run()
