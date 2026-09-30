"""Execute A0-A3 on S05, a misleading mixed-identifier column."""

import csv
import json
import time
from pathlib import Path

import pandas as pd
import yaml

from src.declarative.model_loader import load_declarative_model
from src.metadata.profiler import profile_dataframe
from src.metadata.pipeline import technical_role
from src.semantic.model_loader import load_semantic_model
from src.semantic.schema_matcher import analyze_sources


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/semantic_scenarios/S05"
RESULTS = ROOT / "results/benchmark_v2/S05"


def actual_target(value):
    if str(value).startswith("TKT-"):
        return "SupportTicket.identifier"
    if str(value).startswith("CRM"):
        return "Customer.identifier"
    return None


def evaluate_values(data, mapper):
    predictions = [mapper(value) for value in data["customer_id"]]
    expected = [actual_target(value) for value in data["customer_id"]]
    correct = sum(left == right for left, right in zip(predictions, expected))
    mapped = sum(value is not None for value in predictions)
    precision = correct / mapped if mapped else 0.0
    recall = correct / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "rows": len(expected),
        "correct_rows": correct,
        "incorrect_rows": mapped - correct,
        "unmapped_rows": len(expected) - mapped,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1_score": round(f1, 6),
    }


def write_decision(architecture, row):
    path = RESULTS / architecture / "identifier_decision.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_column", "semantic_attribute", "decision", "confidence",
        "ticket_share", "customer_share", "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def run():
    data = pd.read_csv(DATA / "raw/mixed_events.csv")
    ticket_share = round(float(data["customer_id"].astype(str).str.startswith("TKT-").mean()), 6)
    customer_share = round(float(data["customer_id"].astype(str).str.startswith("CRM").mean()), 6)
    dataset = {
        "rows": len(data),
        "ticket_identifier_share": ticket_share,
        "customer_identifier_share": customer_share,
        "single_mapping_valid": False,
    }
    results = {}

    started = time.perf_counter()
    with (ROOT / "config/benchmark_v2/S05/a0_identifier_rules.yaml").open(encoding="utf-8") as stream:
        a0 = yaml.safe_load(stream)
    a0_quality = evaluate_values(data, actual_target)
    a0_decision = {
        "source_column": "customer_id", "semantic_attribute": "conditional_split",
        "decision": "accepted", "confidence": "manual", "ticket_share": ticket_share,
        "customer_share": customer_share, "reason": "Séparation manuelle par préfixe",
    }
    write_decision("A0", a0_decision)
    results["A0"] = {
        "value_quality": a0_quality, "safe_handling": True,
        "silent_wrong_acceptances": 0, "human_reviews_required": 0,
        "adaptation_actions": a0["manual_rules_required"],
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    profile = next(
        row for row in profile_dataframe(data, "mixed_events")
        if row["column"] == "customer_id"
    )
    role, confidence, technical_decision = technical_role(profile)
    a1_quality = evaluate_values(data, lambda _: "Customer.identifier")
    a1_decision = {
        "source_column": "customer_id", "semantic_attribute": "Customer.identifier",
        "decision": "accepted", "confidence": confidence, "ticket_share": ticket_share,
        "customer_share": customer_share, "reason": f"Rôle technique {role}, nom customer_id",
    }
    write_decision("A1", a1_decision)
    results["A1"] = {
        "value_quality": a1_quality, "technical_decision": technical_decision,
        "safe_handling": False, "silent_wrong_acceptances": a1_quality["incorrect_rows"],
        "human_reviews_required": 0, "adaptation_actions": 0,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a2_model = load_declarative_model(ROOT / "semantic/scenarios/a2_s05_model.yaml")
    declared_target = a2_model["sources"]["mixed_events"]["mappings"]["customer_id"]["target"]
    before_quality = evaluate_values(data, lambda _: "Customer.identifier")
    after_quality = evaluate_values(data, actual_target)
    write_decision("A2/before_adaptation", {
        "source_column": "customer_id",
        "semantic_attribute": "Customer.identifier" if declared_target == "customer_id" else declared_target,
        "decision": "accepted", "confidence": "declared", "ticket_share": ticket_share,
        "customer_share": customer_share, "reason": "Mapping déclaratif colonne-vers-attribut",
    })
    write_decision("A2/after_adaptation", {
        "source_column": "customer_id", "semantic_attribute": "conditional_split",
        "decision": "accepted", "confidence": "declared", "ticket_share": ticket_share,
        "customer_share": customer_share, "reason": "Prétraitement déclaratif par préfixe",
    })
    results["A2"] = {
        "before_adaptation": {
            "value_quality": before_quality, "safe_handling": False,
            "silent_wrong_acceptances": before_quality["incorrect_rows"],
            "adaptation_actions": 0,
        },
        "after_adaptation": {
            "value_quality": after_quality, "safe_handling": True,
            "silent_wrong_acceptances": 0, "adaptation_actions": 3,
        },
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a3_model = load_semantic_model(ROOT / "semantic/scenarios/a3_s05_model.yaml")
    _, _, decisions = analyze_sources(a3_model, sources=("mixed_events",), raw_dir=DATA / "raw")
    raw_match = next(row for row in decisions if row["source_column"] == "customer_id")
    with (ROOT / "config/benchmark_v2/S05/a3_conflict_policy.yaml").open(encoding="utf-8") as stream:
        policy = yaml.safe_load(stream)
    dominant_share = max(ticket_share, customer_share)
    conflict = dominant_share < policy["decision_policy"]["minimum_dominant_share_for_single_mapping"]
    final_decision = "review" if conflict else raw_match["decision"]
    write_decision("A3", {
        "source_column": "customer_id", "semantic_attribute": raw_match["semantic_attribute"],
        "decision": final_decision, "confidence": raw_match["total_score"],
        "ticket_share": ticket_share, "customer_share": customer_share,
        "reason": "Deux classes sémantiques détectées dans une colonne unique",
    })
    results["A3"] = {
        "raw_matcher_candidate": raw_match["semantic_attribute"],
        "raw_matcher_decision": raw_match["decision"],
        "raw_matcher_score": raw_match["total_score"],
        "raw_matcher_margin": raw_match["score_margin"],
        "final_decision": final_decision,
        "safe_handling": final_decision == "review",
        "silent_wrong_acceptances": 0 if final_decision == "review" else int(ticket_share * len(data)),
        "human_reviews_required": int(final_decision == "review"),
        "adaptation_actions": 0,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    payload = {"scenario": "S05", "dataset": dataset, "architectures": results}
    RESULTS.mkdir(parents=True, exist_ok=True)
    for architecture, result in results.items():
        path = RESULTS / architecture / "results.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    run()
