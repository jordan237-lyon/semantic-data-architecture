"""P03: evaluate resilience when two CRM name columns become one."""

import csv
import json
import shutil
from pathlib import Path

import pandas as pd

from src.baseline.pipeline import run as run_baseline
from src.evaluation.evaluate_baseline import evaluate_entity_rows, read_csv
from src.semantic.pipeline import run as run_semantic


ROOT = Path(__file__).resolve().parents[2]
SCENARIO = "p03_merged_name_columns"
SOURCE_RAW = ROOT / "data" / "raw"
SOURCE_TRUTH = ROOT / "data" / "ground_truth"
SCENARIO_DATA = ROOT / "data" / "perturbations" / SCENARIO
SCENARIO_RESULTS = ROOT / "results" / "perturbations" / SCENARIO


def _read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path, fieldnames, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_p03(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, scenario_data=SCENARIO_DATA):
    source_raw, source_truth, scenario_data = map(Path, (source_raw, source_truth, scenario_data))
    raw_dir, truth_dir = scenario_data / "raw", scenario_data / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_raw / "support.csv", raw_dir / "support.csv")
    shutil.copy2(source_raw / "finance.csv", raw_dir / "finance.csv")
    shutil.copy2(source_truth / "entity_mapping.csv", truth_dir / "entity_mapping.csv")

    crm = pd.read_csv(source_raw / "crm.csv")
    crm["customer_name"] = (
        crm["first_name"].fillna("").str.strip()
        + " "
        + crm["last_name"].fillna("").str.strip()
    ).str.strip()
    crm = crm[["client_id", "customer_name", "email", "country", "created_at"]]
    crm.to_csv(raw_dir / "crm.csv", index=False)

    schema_rows = _read_csv(source_truth / "schema_mapping.csv")
    schema_rows = [
        row for row in schema_rows
        if not (row["source"] == "crm" and row["source_column"] in {"first_name", "last_name"})
    ]
    schema_rows.append({
        "source": "crm", "source_column": "customer_name",
        "semantic_attribute": "Customer.full_name", "references": "",
    })
    _write_csv(
        truth_dir / "schema_mapping.csv",
        ["source", "source_column", "semantic_attribute", "references"],
        schema_rows,
    )

    manifest = {
        "scenario": SCENARIO,
        "description": "Fusion structurelle de deux colonnes CRM en un nom complet.",
        "change": {
            "source": "crm", "before": ["first_name", "last_name"],
            "after": ["customer_name"], "column_count_delta": -1,
            "values_modified": False,
        },
    }
    (scenario_data / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def run_p03():
    manifest = generate_p03()
    raw_dir = SCENARIO_DATA / "raw"
    truth_dir = SCENARIO_DATA / "ground_truth"
    output_dir = SCENARIO_DATA / "output"
    SCENARIO_RESULTS.mkdir(parents=True, exist_ok=True)

    baseline_output = output_dir / "baseline" / "unified_customer_baseline.csv"
    baseline = {
        "status": "not_run",
        "code_changes_applied": 1,
        "adaptation": {
            "type": "conditional_python_schema_rule",
            "files_modified": ["src/baseline/transform.py", "src/baseline/pipeline.py"],
            "rules_added": 1,
        },
    }
    try:
        run_baseline(
            raw_dir=raw_dir, output_dir=output_dir / "baseline",
            results_dir=SCENARIO_RESULTS / "baseline",
        )
        evaluation, _ = evaluate_entity_rows(
            read_csv(truth_dir / "entity_mapping.csv"), read_csv(baseline_output)
        )
        baseline.update(
            status="success",
            adaptation_required=False,
            entity_quality=evaluation["overall"],
        )
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        baseline.update(status="failed", adaptation_required=True, error=message)
        (SCENARIO_RESULTS / "baseline_error.txt").write_text(message + "\n", encoding="utf-8")

    semantic_results = SCENARIO_RESULTS / "semantic"
    semantic_output = output_dir / "unified_customer_semantic.csv"
    semantic_status, semantic_error = "success", None
    try:
        run_semantic(
            raw_dir=raw_dir, output_path=semantic_output,
            results_dir=semantic_results,
            ground_truth_path=truth_dir / "entity_mapping.csv",
        )
    except ValueError as error:
        semantic_status = "requires_review"
        semantic_error = f"{type(error).__name__}: {error}"

    decisions = _read_csv(semantic_results / "schema_decisions.csv")
    mapping = next(
        row for row in decisions
        if row["source"] == "crm" and row["source_column"] == "customer_name"
    )
    semantic = {
        "status": semantic_status,
        "code_changes_applied": 0,
        "adaptation_required": semantic_status != "success",
        "perturbed_column_mapping": mapping,
        "mapping_matches_ground_truth": mapping["semantic_attribute"] == "Customer.full_name",
        "incremental_human_validations": int(mapping["decision"] == "review"),
        "adaptation": {
            "type": "none",
            "files_modified": [],
            "rules_added": 0,
        },
    }
    if semantic_error:
        semantic["error"] = semantic_error
    else:
        metrics = json.loads(
            (semantic_results / "semantic_pipeline_metrics.json").read_text(encoding="utf-8")
        )
        semantic["entity_quality"] = {
            "precision": metrics["entity_precision"],
            "recall": metrics["entity_recall"],
            "f1_score": metrics["entity_f1_score"],
        }

    result = {
        **manifest,
        "phase": "after_adaptation",
        "baseline": baseline,
        "semantic": semantic,
        "interpretation": "La baseline exige une branche conditionnelle ; la sémantique absorbe automatiquement la structure fusionnée.",
    }
    (SCENARIO_RESULTS / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run_p03()
