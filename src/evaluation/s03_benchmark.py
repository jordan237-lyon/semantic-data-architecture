"""Evaluate A0-A3 on S03: competing gross and net revenue definitions."""

import csv
import json
import time
from pathlib import Path

import pandas as pd
import yaml

from src.declarative.model_loader import load_declarative_model
from src.semantic.model_loader import load_semantic_model
from src.semantic.schema_matcher import analyze_sources


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/semantic_scenarios/S03"
RESULTS = ROOT / "results/benchmark_v2/S03"
TRUTH = {
    ("revenue_gross", "gross_revenue"): "RevenueSnapshot.gross_revenue",
    ("revenue_net", "net_revenue"): "RevenueSnapshot.net_revenue",
}


def semantic_metrics(decisions):
    rows = [row for row in decisions if (row["source"], row["source_column"]) in TRUTH]
    accepted = [row for row in rows if row["decision"] == "accepted"]
    correct = lambda row: row.get("semantic_attribute") == TRUTH[(row["source"], row["source_column"])]
    accepted_correct = sum(correct(row) for row in accepted)
    candidate_correct = sum(correct(row) for row in rows)
    confused = sum(
        row.get("semantic_attribute")
        in {"RevenueSnapshot.gross_revenue", "RevenueSnapshot.net_revenue"}
        and not correct(row)
        for row in rows
    )
    precision = accepted_correct / len(accepted) if accepted else 0.0
    recall = accepted_correct / len(TRUTH)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "expected_mappings": len(TRUTH),
        "accepted_correct": accepted_correct,
        "accepted_incorrect": len(accepted) - accepted_correct,
        "gross_net_confusions": confused,
        "review_mappings": sum(row["decision"] == "review" for row in rows),
        "candidate_accuracy": round(candidate_correct / len(TRUTH), 6),
        "coverage": round(len(accepted) / len(TRUTH), 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1_score": round(f1, 6),
    }


def write_decisions(architecture, decisions):
    path = RESULTS / architecture / "revenue_decisions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source", "source_column", "semantic_attribute", "decision",
        "confidence", "score_margin", "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in decisions)


def dataset_checks():
    gross = pd.read_csv(DATA / "raw/revenue_gross.csv")
    net = pd.read_csv(DATA / "raw/revenue_net.csv")
    joined = gross.merge(net, on=["account_id", "customer_email", "period", "currency"])
    return {
        "gross_rows": len(gross),
        "net_rows": len(net),
        "distinct_customers": int(joined["account_id"].nunique()),
        "distinct_periods": int(joined["period"].nunique()),
        "grain": "customer_month",
        "all_net_below_gross": bool((joined["net_revenue"] < joined["gross_revenue"]).all()),
        "gross_net_correlation": round(float(joined["gross_revenue"].corr(joined["net_revenue"])), 6),
    }


def declared_decisions(model_path):
    model = load_declarative_model(model_path)
    decisions = []
    for source, column in TRUTH:
        target = model["sources"][source]["mappings"][column]["target"]
        decisions.append({
            "source": source,
            "source_column": column,
            "semantic_attribute": f"RevenueSnapshot.{target}",
            "decision": "accepted",
            "confidence": "declared",
            "reason": "Mapping YAML prédéfini avec définition métier distincte",
        })
    return decisions


def run():
    results = {}

    started = time.perf_counter()
    with (ROOT / "config/benchmark_v2/S03/a0_manual_mappings.yaml").open(encoding="utf-8") as stream:
        mappings = yaml.safe_load(stream)["sources"]
    a0_decisions = [
        {
            "source": source,
            "source_column": column,
            "semantic_attribute": mappings[source]["mappings"][column],
            "decision": "accepted",
            "confidence": "manual",
            "reason": "Règle ETL manuelle distinguant brut et net",
        }
        for source, column in TRUTH
    ]
    write_decisions("A0", a0_decisions)
    results["A0"] = {
        "semantic_quality": semantic_metrics(a0_decisions),
        "manual_semantic_rules": 2,
        "grain_handling": "manual_rule_required",
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a1_decisions = [
        {
            "source": source,
            "source_column": column,
            "semantic_attribute": "",
            "decision": "review",
            "confidence": 0.8,
            "reason": "Mesure numérique : définition comptable indéductible des métadonnées techniques",
        }
        for source, column in TRUTH
    ]
    write_decisions("A1", a1_decisions)
    results["A1"] = {
        "semantic_quality": semantic_metrics(a1_decisions),
        "human_reviews_required": 2,
        "grain_handling": "technical_profile_only",
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a2_decisions = declared_decisions(ROOT / "semantic/scenarios/a2_s03_model.yaml")
    write_decisions("A2", a2_decisions)
    results["A2"] = {
        "semantic_quality": semantic_metrics(a2_decisions),
        "declarative_semantic_mappings": 2,
        "grain_handling": "declared_customer_month",
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a3_model = load_semantic_model(ROOT / "semantic/scenarios/a3_s03_model.yaml")
    _, _, decisions = analyze_sources(
        a3_model,
        sources=("revenue_gross", "revenue_net"),
        raw_dir=DATA / "raw",
    )
    a3_decisions = [
        {
            "source": row["source"],
            "source_column": row["source_column"],
            "semantic_attribute": row["semantic_attribute"],
            "decision": row["decision"],
            "confidence": row["total_score"],
            "score_margin": row["score_margin"],
            "reason": row["decision_reason"],
        }
        for row in decisions
        if (row["source"], row["source_column"]) in TRUTH
    ]
    write_decisions("A3", a3_decisions)
    results["A3"] = {
        "semantic_quality": semantic_metrics(a3_decisions),
        "human_reviews_required": sum(row["decision"] == "review" for row in a3_decisions),
        "grain_handling": "semantic_customer_month",
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    payload = {"scenario": "S03", "dataset_checks": dataset_checks(), "architectures": results}
    for architecture, result in results.items():
        path = RESULTS / architecture / "results.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    run()
