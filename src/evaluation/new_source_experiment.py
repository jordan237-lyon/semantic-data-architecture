"""Evaluate a fourth, previously unknown loyalty source before adaptation."""

import csv
import json
import shutil
from pathlib import Path

import pandas as pd

from src.baseline.pipeline import run as run_baseline
from src.evaluation.metrics import evaluate_pairs
from src.semantic.model_loader import load_semantic_model
from src.semantic.pipeline import run as run_semantic
from src.semantic.schema_matcher import analyze_sources


ROOT = Path(__file__).resolve().parents[2]
SOURCE_RAW = ROOT / "data" / "raw"
SOURCE_TRUTH = ROOT / "data" / "ground_truth"
DATA = ROOT / "data" / "new_source" / "loyalty"
RESULTS = ROOT / "results" / "new_source" / "loyalty" / "before_adaptation"
AFTER_RESULTS = ROOT / "results" / "new_source" / "loyalty" / "after_adaptation"
COUNTRY_TO_CODE = {
    "France": "FR", "Cameroon": "CM", "Germany": "DE", "Spain": "ES",
    "Belgium": "BE", "Canada": "CA", "Italy": "IT",
}


def _write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def generate_loyalty_source(
    source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, destination=DATA, member_count=80
):
    source_raw, source_truth, destination = map(
        Path, (source_raw, source_truth, destination)
    )
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    for source in ("crm", "support", "finance"):
        shutil.copy2(source_raw / f"{source}.csv", raw_dir / f"{source}.csv")

    crm = pd.read_csv(source_raw / "crm.csv").head(member_count).copy()
    loyalty = pd.DataFrame({
        "member_id": [f"LOY{index:04d}" for index in range(1, len(crm) + 1)],
        "display_name": (
            crm["first_name"].fillna("") + " " + crm["last_name"].fillna("")
        ).str.upper(),
        "email_address": crm["email"].str.upper().map(lambda value: f" {value} "),
        "market": crm["country"].map(COUNTRY_TO_CODE),
        "joined_on": crm["created_at"],
    })
    loyalty.to_csv(raw_dir / "loyalty.csv", index=False)

    truth = pd.read_csv(source_truth / "entity_mapping.csv", dtype="string")
    loyalty_by_crm = dict(zip(crm["client_id"], loyalty["member_id"]))
    truth["loyalty_member_id"] = truth["crm_client_id"].map(loyalty_by_crm)
    truth.to_csv(truth_dir / "entity_mapping.csv", index=False)

    schema = pd.read_csv(source_truth / "schema_mapping.csv", dtype="string")
    additions = pd.DataFrame([
        {"source": "loyalty", "source_column": "member_id", "semantic_attribute": "Customer.identifier", "references": ""},
        {"source": "loyalty", "source_column": "display_name", "semantic_attribute": "Customer.full_name", "references": ""},
        {"source": "loyalty", "source_column": "email_address", "semantic_attribute": "Customer.email", "references": ""},
        {"source": "loyalty", "source_column": "market", "semantic_attribute": "Customer.country", "references": ""},
        {"source": "loyalty", "source_column": "joined_on", "semantic_attribute": "Customer.created_at", "references": ""},
    ])
    pd.concat([schema, additions], ignore_index=True).to_csv(
        truth_dir / "schema_mapping.csv", index=False
    )
    manifest = {
        "source": "loyalty",
        "rows": int(len(loyalty)),
        "columns": list(loyalty.columns),
        "known_to_initial_pipelines": False,
        "granularity": "one row per loyalty member",
    }
    (destination / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def run_before_adaptation():
    manifest = generate_loyalty_source()
    raw_dir = DATA / "raw"
    truth_dir = DATA / "ground_truth"
    output_dir = DATA / "output_before_adaptation"
    RESULTS.mkdir(parents=True, exist_ok=True)

    run_baseline(
        raw_dir=raw_dir, output_dir=output_dir / "baseline",
        results_dir=RESULTS / "baseline",
    )
    semantic_output = output_dir / "unified_customer_semantic.csv"
    run_semantic(
        raw_dir=raw_dir, output_path=semantic_output,
        results_dir=RESULTS / "semantic",
        ground_truth_path=truth_dir / "entity_mapping.csv",
    )

    model = load_semantic_model()
    _, _, decisions = analyze_sources(
        model=model, sources=("loyalty",), raw_dir=raw_dir
    )
    with (RESULTS / "loyalty_schema_decisions.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)

    expected = {
        row["source_column"]: row["semantic_attribute"]
        for row in pd.read_csv(truth_dir / "schema_mapping.csv").fillna("").to_dict("records")
        if row["source"] == "loyalty"
    }
    correct = sum(
        row["semantic_attribute"] == expected[row["source_column"]]
        for row in decisions
    )
    result = {
        "phase": "before_adaptation",
        "new_source": manifest,
        "baseline": {
            "pipeline_status": "success_but_source_ignored",
            "loyalty_rows_integrated": 0,
            "source_coverage": 0.0,
            "reason": "The source list is hard-coded to CRM, support and finance.",
        },
        "semantic": {
            "pipeline_status": "success_but_source_ignored",
            "loyalty_rows_integrated": 0,
            "source_coverage": 0.0,
            "reason": "The pipeline orchestration is also hard-coded to three sources.",
            "standalone_schema_analysis": {
                "columns_profiled": len(decisions),
                "correct_best_candidates": correct,
                "schema_precision": round(correct / len(decisions), 6),
                "accepted": sum(row["decision"] == "accepted" for row in decisions),
                "review": sum(row["decision"] == "review" for row in decisions),
                "rejected": sum(row["decision"] == "rejected" for row in decisions),
            },
        },
        "conclusion": "Neither pipeline discovers the fourth source yet; the semantic matcher can still analyze its schema independently.",
    }
    (RESULTS / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def _loyalty_quality(truth_path, output_path, loyalty_column):
    truth = pd.read_csv(truth_path, dtype="string").fillna("")
    output = pd.read_csv(output_path, dtype="string").fillna("")
    expected = {
        (row.crm_client_id, row.loyalty_member_id)
        for row in truth.itertuples()
        if row.crm_client_id and row.loyalty_member_id
    }
    predicted = {
        (row["crm_client_id"], row[loyalty_column])
        for row in output.to_dict("records")
        if row.get("crm_client_id") and row.get(loyalty_column)
    }
    return evaluate_pairs(predicted, expected)


def run_after_adaptation():
    manifest = generate_loyalty_source()
    raw_dir = DATA / "raw"
    truth_path = DATA / "ground_truth" / "entity_mapping.csv"
    output_dir = DATA / "output_after_adaptation"
    AFTER_RESULTS.mkdir(parents=True, exist_ok=True)

    run_baseline(
        raw_dir=raw_dir, output_dir=output_dir / "baseline",
        results_dir=AFTER_RESULTS / "baseline",
    )
    baseline_output = output_dir / "baseline" / "unified_customer_baseline.csv"
    semantic_output = output_dir / "unified_customer_semantic.csv"
    run_semantic(
        raw_dir=raw_dir, output_path=semantic_output,
        results_dir=AFTER_RESULTS / "semantic", ground_truth_path=truth_path,
    )
    decisions = pd.read_csv(
        AFTER_RESULTS / "semantic" / "schema_decisions.csv"
    ).fillna("")
    loyalty_decisions = decisions[decisions["source"] == "loyalty"]
    baseline_metrics = json.loads(
        (AFTER_RESULTS / "baseline" / "baseline_metrics.json").read_text(encoding="utf-8")
    )
    semantic_metrics = json.loads(
        (AFTER_RESULTS / "semantic" / "semantic_pipeline_metrics.json").read_text(encoding="utf-8")
    )
    result = {
        "phase": "after_adaptation",
        "new_source": manifest,
        "baseline": {
            "pipeline_status": "success", "source_coverage": 1.0,
            "loyalty_quality": _loyalty_quality(truth_path, baseline_output, "loyalty_member_id"),
            "adaptation": {
                "manual_schema_mappings_added": 5, "manual_rules_added": 5,
                "python_files_modified": 2,
            },
            "execution_time_seconds": baseline_metrics["execution_time_seconds"],
        },
        "semantic": {
            "pipeline_status": "success", "source_coverage": 1.0,
            "loyalty_quality": _loyalty_quality(truth_path, semantic_output, "loyalty_identifier"),
            "adaptation": {
                "yaml_synonyms_added": 4,
                "generic_orchestration_python_files_modified": 2,
                "incremental_human_validations": 0,
            },
            "loyalty_schema_decisions": {
                "accepted": int((loyalty_decisions["decision"] == "accepted").sum()),
                "review": int((loyalty_decisions["decision"] == "review").sum()),
                "rejected": int((loyalty_decisions["decision"] == "rejected").sum()),
            },
            "execution_time_seconds": semantic_metrics["execution_time_seconds"],
        },
        "measurement_note": "Effort is counted as mappings, rules, validations and modified artifacts, not elapsed human hours.",
    }
    (AFTER_RESULTS / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run_after_adaptation()
