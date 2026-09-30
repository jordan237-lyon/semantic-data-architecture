"""Execute A0-A3 on S04, an unchanged column with temporal semantic drift."""

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
DATA = ROOT / "data/semantic_scenarios/S04"
RESULTS = ROOT / "results/benchmark_v2/S04"
EXPECTED = {
    "before": "Customer.recently_active_90d",
    "after": "Customer.paying_contract_active",
}


def window_statistics():
    data = pd.read_csv(DATA / "raw/customer_activity.csv")
    data["snapshot_date"] = pd.to_datetime(data["snapshot_date"])
    before = data[data["snapshot_date"] < "2025-07-01"]["active"].astype(bool)
    after = data[data["snapshot_date"] >= "2025-07-01"]["active"].astype(bool)
    before_rate, after_rate = float(before.mean()), float(after.mean())
    return {
        "before_rows": len(before),
        "after_rows": len(after),
        "before_true_rate": round(before_rate, 6),
        "after_true_rate": round(after_rate, 6),
        "absolute_rate_change": round(abs(after_rate - before_rate), 6),
    }


def write_decisions(architecture, rows):
    path = RESULTS / architecture / "drift_decisions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "phase", "source_column", "semantic_attribute", "decision",
        "confidence", "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def outcome(decisions, *, drift_detected, adaptation_actions):
    correct = sum(
        row.get("semantic_attribute") == EXPECTED.get(row["phase"])
        for row in decisions
        if row["decision"] == "accepted" and row["phase"] in EXPECTED
    )
    reviews = sum(row["decision"] == "review" for row in decisions)
    silent = sum(
        row["decision"] == "accepted"
        and row["phase"] == "after"
        and row.get("semantic_attribute") != EXPECTED["after"]
        for row in decisions
    )
    return {
        "drift_detected": drift_detected,
        "correct_temporal_mappings": correct,
        "expected_temporal_mappings": 2,
        "human_reviews_required": reviews,
        "silent_wrong_acceptances": silent,
        "safe_handling": bool(drift_detected and silent == 0),
        "adaptation_actions": adaptation_actions,
    }


def run():
    statistics = window_statistics()
    results = {}

    started = time.perf_counter()
    with (ROOT / "config/benchmark_v2/S04/a0_temporal_rules.yaml").open(encoding="utf-8") as stream:
        a0 = yaml.safe_load(stream)
    a0_decisions = [
        {
            "phase": phase,
            "source_column": "active",
            "semantic_attribute": rule["target"],
            "decision": "accepted",
            "confidence": "manual",
            "reason": rule["condition"],
        }
        for phase, rule in zip(("before", "after"), a0["rules"])
    ]
    write_decisions("A0", a0_decisions)
    results["A0"] = {
        **outcome(a0_decisions, drift_detected=True, adaptation_actions=2),
        "handling": "manual_temporal_rules",
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    with (ROOT / "config/benchmark_v2/S04/a1_drift_policy.yaml").open(encoding="utf-8") as stream:
        a1 = yaml.safe_load(stream)
    threshold = a1["comparison"]["absolute_change_threshold"]
    detected = statistics["absolute_rate_change"] >= threshold
    a1_decisions = [{
        "phase": "drift",
        "source_column": "active",
        "semantic_attribute": "",
        "decision": "review" if detected else "accepted",
        "confidence": round(statistics["absolute_rate_change"], 6),
        "reason": "Variation de distribution sans définition métier disponible",
    }]
    write_decisions("A1", a1_decisions)
    results["A1"] = {
        **outcome(a1_decisions, drift_detected=detected, adaptation_actions=0),
        "handling": "technical_distribution_alert",
        "threshold": threshold,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    before_model = load_declarative_model(ROOT / "semantic/scenarios/a2_s04_before_model.yaml")
    initial_target = before_model["sources"]["customer_activity"]["mappings"]["active"]["target"]
    before_adaptation = [
        {"phase": "before", "source_column": "active", "semantic_attribute": f"Customer.{initial_target}", "decision": "accepted", "confidence": "declared", "reason": "Mapping statique initial"},
        {"phase": "after", "source_column": "active", "semantic_attribute": f"Customer.{initial_target}", "decision": "accepted", "confidence": "declared", "reason": "Mapping initial réutilisé silencieusement"},
    ]
    after_model = load_declarative_model(ROOT / "semantic/scenarios/a2_s04_after_model.yaml")
    adapted_target = after_model["sources"]["customer_activity"]["mappings"]["active"]["target"]
    after_adaptation = [
        before_adaptation[0],
        {"phase": "after", "source_column": "active", "semantic_attribute": f"Customer.{adapted_target}", "decision": "accepted", "confidence": "declared", "reason": "Nouvelle version déclarative"},
    ]
    write_decisions("A2/before_adaptation", before_adaptation)
    write_decisions("A2/after_adaptation", after_adaptation)
    results["A2"] = {
        "before_adaptation": outcome(before_adaptation, drift_detected=False, adaptation_actions=0),
        "after_adaptation": outcome(after_adaptation, drift_detected=True, adaptation_actions=1),
        "handling": "versioned_declarative_mapping",
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    started = time.perf_counter()
    a3_model = load_semantic_model(ROOT / "semantic/scenarios/a3_s04_model.yaml")
    _, _, matcher_decisions = analyze_sources(
        a3_model, sources=("customer_activity",), raw_dir=DATA / "raw"
    )
    active = next(row for row in matcher_decisions if row["source_column"] == "active")
    with (ROOT / "config/benchmark_v2/S04/a3_drift_policy.yaml").open(encoding="utf-8") as stream:
        a3_policy = yaml.safe_load(stream)
    detected = statistics["absolute_rate_change"] >= a3_policy["detection"]["absolute_change_threshold"]
    a3_decisions = [{
        "phase": "drift",
        "source_column": "active",
        "semantic_attribute": active["semantic_attribute"],
        "decision": "review" if detected else active["decision"],
        "confidence": active["total_score"],
        "reason": "Rupture temporelle et définitions concurrentes",
    }]
    write_decisions("A3", a3_decisions)
    results["A3"] = {
        **outcome(a3_decisions, drift_detected=detected, adaptation_actions=0),
        "handling": "semantic_temporal_review",
        "matcher_candidate": active["semantic_attribute"],
        "matcher_margin": active["score_margin"],
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }

    payload = {"scenario": "S04", "window_statistics": statistics, "architectures": results}
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
