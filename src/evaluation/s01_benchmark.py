"""Execute the frozen A0-A3 configurations on semantic scenario S01."""

import csv
import io
import json
import time
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from src.baseline.pipeline import run as run_a0
from src.declarative.model_loader import load_declarative_model
from src.declarative.pipeline import run as run_a2
from src.evaluation.evaluate_baseline import evaluate_entity_rows, read_csv
from src.metadata.pipeline import run as run_a1
from src.semantic.model_loader import load_semantic_model
from src.semantic.schema_matcher import analyze_sources

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/semantic_scenarios/S01"
RESULTS = ROOT / "results/benchmark_v2/S01"
OUTPUTS = ROOT / "data/output/benchmark_v2/S01"
STATUS_TRUTH = {
    ("crm", "status"): "Customer.customer_status",
    ("support", "status"): "SupportTicket.ticket_status",
}


def schema_metrics(decisions):
    """Score accepted mappings separately from correct candidates in review."""
    rows = [row for row in decisions if (row["source"], row["source_column"]) in STATUS_TRUTH]
    total = len(STATUS_TRUTH)
    accepted = [row for row in rows if row["decision"] == "accepted"]
    accepted_correct = sum(
        row.get("semantic_attribute") == STATUS_TRUTH[(row["source"], row["source_column"])]
        for row in accepted
    )
    correct_candidates = sum(
        row.get("semantic_attribute") == STATUS_TRUTH[(row["source"], row["source_column"])]
        for row in rows
    )
    accepted_incorrect = len(accepted) - accepted_correct
    precision = accepted_correct / len(accepted) if accepted else 0.0
    recall = accepted_correct / total
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "expected_mappings": total,
        "accepted_mappings": len(accepted),
        "accepted_correct": accepted_correct,
        "accepted_incorrect": accepted_incorrect,
        "review_mappings": sum(row["decision"] == "review" for row in rows),
        "rejected_mappings": sum(row["decision"] == "rejected" for row in rows),
        "candidate_accuracy": round(correct_candidates / total, 6),
        "coverage": round(len(accepted) / total, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1_score": round(f1, 6),
    }


def write_decisions(path, decisions):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source", "source_column", "semantic_attribute", "decision", "confidence", "reason"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in decisions)


def entity_quality(path):
    evaluation, _ = evaluate_entity_rows(
        read_csv(DATA / "ground_truth/entity_mapping.csv"), read_csv(path)
    )
    return evaluation["overall"]


def run():
    results = {}

    started = time.perf_counter()
    a0_dir = RESULTS / "A0"
    with redirect_stdout(io.StringIO()):
        run_a0(raw_dir=DATA / "raw", output_dir=OUTPUTS / "A0", results_dir=a0_dir)
    with (ROOT / "config/benchmark_v2/S01/a0_manual_mappings.yaml").open(encoding="utf-8") as stream:
        rules = yaml.safe_load(stream)["rules"]
    a0_decisions = [
        {
            "source": rule["source"], "source_column": rule["source_column"],
            "semantic_attribute": rule["target"], "decision": "accepted",
            "confidence": "manual", "reason": "Règle manuelle explicite",
        }
        for rule in rules
    ]
    write_decisions(a0_dir / "status_decisions.csv", a0_decisions)
    results["A0"] = {
        "schema_quality": schema_metrics(a0_decisions),
        "entity_quality": entity_quality(OUTPUTS / "A0/unified_customer_baseline.csv"),
        "human_rules": 2,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a1_dir = RESULTS / "A1"
    with redirect_stdout(io.StringIO()):
        a1_metrics = run_a1(
            raw_dir=DATA / "raw", output_path=OUTPUTS / "A1/unified_customer_a1.csv",
            results_dir=a1_dir, ground_truth_path=DATA / "ground_truth/entity_mapping.csv",
        )
    a1_decisions = [
        {
            "source": source, "source_column": "status", "semantic_attribute": "",
            "decision": "review", "confidence": 0.5,
            "reason": "Texte non classifiable avec les métadonnées techniques",
        }
        for source in ("crm", "support")
    ]
    write_decisions(a1_dir / "status_decisions.csv", a1_decisions)
    results["A1"] = {
        "schema_quality": schema_metrics(a1_decisions),
        "entity_quality": a1_metrics["entity_quality"],
        "human_reviews_required": 2,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a2_dir = RESULTS / "A2"
    a2_model_path = ROOT / "semantic/scenarios/a2_s01_model.yaml"
    with redirect_stdout(io.StringIO()):
        a2_metrics = run_a2(
            raw_dir=DATA / "raw", output_path=OUTPUTS / "A2/unified_customer_a2.csv",
            results_dir=a2_dir, ground_truth_path=DATA / "ground_truth/entity_mapping.csv",
            model_path=a2_model_path,
        )
    a2_model = load_declarative_model(a2_model_path)
    a2_targets = {"customer_status": "Customer.customer_status", "ticket_status": "SupportTicket.ticket_status"}
    a2_decisions = [
        {
            "source": source, "source_column": "status",
            "semantic_attribute": a2_targets[a2_model["sources"][source]["mappings"]["status"]["target"]],
            "decision": "accepted", "confidence": "declared",
            "reason": "Mapping YAML prédéfini",
        }
        for source in ("crm", "support")
    ]
    write_decisions(a2_dir / "status_decisions.csv", a2_decisions)
    results["A2"] = {
        "schema_quality": schema_metrics(a2_decisions),
        "entity_quality": a2_metrics["entity_quality"],
        "declarative_mappings": 2,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a3_dir = RESULTS / "A3"
    a3_model = load_semantic_model(ROOT / "semantic/scenarios/a3_s01_model.yaml")
    _, _, all_decisions = analyze_sources(
        a3_model, sources=("crm", "support", "finance"), raw_dir=DATA / "raw"
    )
    selected = [row for row in all_decisions if row["source_column"] == "status"]
    a3_decisions = [
        {
            "source": row["source"], "source_column": row["source_column"],
            "semantic_attribute": row["semantic_attribute"], "decision": row["decision"],
            "confidence": row["total_score"], "reason": row["decision_reason"],
        }
        for row in selected
    ]
    write_decisions(a3_dir / "status_decisions.csv", a3_decisions)
    results["A3"] = {
        "schema_quality": schema_metrics(a3_decisions),
        "entity_quality": None,
        "pipeline_status": "schema_review_required",
        "human_reviews_required": sum(row["decision"] == "review" for row in a3_decisions),
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    for architecture, result in results.items():
        path = RESULTS / architecture / "results.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "summary.json").write_text(
        json.dumps({"scenario": "S01", "architectures": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    run()
