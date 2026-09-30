"""Generate and run isolated schema-perturbation experiments."""

import csv
import json
import shutil
from pathlib import Path

from src.baseline.pipeline import run as run_baseline
from src.semantic.pipeline import run as run_semantic


ROOT = Path(__file__).resolve().parents[2]
SOURCE_RAW = ROOT / "data" / "raw"
SOURCE_GROUND_TRUTH = ROOT / "data" / "ground_truth"
SCENARIO_NAME = "p01_renamed_column"
SCENARIO_DATA = ROOT / "data" / "perturbations" / SCENARIO_NAME
SCENARIO_RESULTS = ROOT / "results" / "perturbations" / SCENARIO_NAME


def _read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path, fieldnames, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_p01(source_raw=SOURCE_RAW, source_ground_truth=SOURCE_GROUND_TRUTH, scenario_data=SCENARIO_DATA):
    source_raw = Path(source_raw)
    source_ground_truth = Path(source_ground_truth)
    scenario_data = Path(scenario_data)
    raw_dir = scenario_data / "raw"
    truth_dir = scenario_data / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_raw / "crm.csv", raw_dir / "crm.csv")
    shutil.copy2(source_raw / "finance.csv", raw_dir / "finance.csv")
    support_rows = _read_csv(source_raw / "support.csv")
    for row in support_rows:
        row["customer_email_address"] = row.pop("mail")
    support_fields = [
        "ticket_id",
        "customer_ref",
        "full_name",
        "customer_email_address",
        "country_name",
        "created_at",
    ]
    _write_csv(raw_dir / "support.csv", support_fields, support_rows)

    shutil.copy2(
        source_ground_truth / "entity_mapping.csv",
        truth_dir / "entity_mapping.csv",
    )
    schema_rows = _read_csv(source_ground_truth / "schema_mapping.csv")
    for row in schema_rows:
        if row["source"] == "support" and row["source_column"] == "mail":
            row["source_column"] = "customer_email_address"
    _write_csv(
        truth_dir / "schema_mapping.csv",
        ["source", "source_column", "semantic_attribute", "references"],
        schema_rows,
    )

    manifest = {
        "scenario": SCENARIO_NAME,
        "description": "Renommage isolé de la colonne e-mail du support.",
        "change": {
            "source": "support",
            "before": "mail",
            "after": "customer_email_address",
            "values_modified": False,
        },
    }
    (scenario_data / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def run_p01():
    manifest = generate_p01()
    raw_dir = SCENARIO_DATA / "raw"
    truth_dir = SCENARIO_DATA / "ground_truth"
    output_dir = SCENARIO_DATA / "output"
    SCENARIO_RESULTS.mkdir(parents=True, exist_ok=True)

    baseline_result = {
        "status": "not_run",
        "code_changes_applied": 0,
        "adaptation_required": None,
    }
    try:
        run_baseline(
            raw_dir=raw_dir,
            output_dir=output_dir / "baseline",
            results_dir=SCENARIO_RESULTS / "baseline",
        )
        baseline_result.update(status="success", adaptation_required=False)
    except Exception as error:  # The experiment intentionally captures breakage.
        message = f"{type(error).__name__}: {error}"
        baseline_result.update(
            status="failed",
            adaptation_required=True,
            error=message,
        )
        (SCENARIO_RESULTS / "baseline_error.txt").write_text(
            message + "\n", encoding="utf-8"
        )

    semantic_results = SCENARIO_RESULTS / "semantic"
    scenario_validations = SCENARIO_DATA / "human_validations.yaml"
    semantic_status = "success"
    semantic_error = None
    try:
        run_semantic(
            raw_dir=raw_dir,
            output_path=output_dir / "unified_customer_semantic.csv",
            results_dir=semantic_results,
            ground_truth_path=truth_dir / "entity_mapping.csv",
            validations_path=(
                scenario_validations if scenario_validations.exists() else None
            )
            or ROOT / "semantic" / "human_validations.yaml",
        )
    except ValueError as error:
        semantic_status = "requires_review"
        semantic_error = f"{type(error).__name__}: {error}"
    decisions = _read_csv(semantic_results / "schema_decisions.csv")
    target_decision = next(
        row
        for row in decisions
        if row["source"] == "support"
        and row["source_column"] == "customer_email_address"
    )
    expected_mapping = next(
        row["semantic_attribute"]
        for row in _read_csv(truth_dir / "schema_mapping.csv")
        if row["source"] == "support"
        and row["source_column"] == "customer_email_address"
    )
    semantic_result = {
        "status": semantic_status,
        "code_changes_applied": 0,
        "adaptation_required": semantic_status != "success",
        "perturbed_column_mapping": target_decision,
        "mapping_matches_ground_truth": (
            target_decision["semantic_attribute"] == expected_mapping
        ),
        "incremental_human_validations": int(
            target_decision["decision"] == "review"
        ),
    }
    if semantic_status == "success" and target_decision["decision"] == "review":
        semantic_result["adaptation"] = {
            "type": "human_validation",
            "files_modified": 1,
            "code_lines_modified": 0,
            "mapping_validated": target_decision["semantic_attribute"],
        }
    if semantic_error:
        semantic_result["error"] = semantic_error
    else:
        semantic_metrics = json.loads(
            (semantic_results / "semantic_pipeline_metrics.json").read_text(
                encoding="utf-8"
            )
        )
        semantic_result["entity_quality"] = {
            "precision": semantic_metrics["entity_precision"],
            "recall": semantic_metrics["entity_recall"],
            "f1_score": semantic_metrics["entity_f1_score"],
        }

    result = {
        **manifest,
        "baseline": baseline_result,
        "semantic": semantic_result,
    }
    (SCENARIO_RESULTS / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_p01()
