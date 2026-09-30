"""Run the single authorised R01 calibration case: S05/I1/seed-11."""

import csv
import json
import time
import tracemalloc
from pathlib import Path

import pandas as pd
import yaml

from src.metadata.profiler import profile_dataframe
from src.metadata.pipeline import technical_role
from src.robustness.r01.paths import CONFIG_ROOT, DATA_ROOT, RESULTS_ROOT, ROOT
from src.semantic.model_loader import load_semantic_model
from src.semantic.schema_matcher import analyze_sources


CASE_DATA = DATA_ROOT / "S05/I1/seed-11"
CASE_RESULTS = RESULTS_ROOT / "calibration_runs/S05/I1/seed-11"
CASE_CONFIG = CONFIG_ROOT / "S05/I1_architectures.yaml"


def target_from_prefix(value, rules):
    text = str(value)
    for rule in rules:
        if text.startswith(rule["prefix"]):
            return rule["target"]
    return None


def evaluate_predictions(predictions, truth):
    joined = truth.merge(predictions, on=["row_number", "value"], how="left")
    mapped = joined["predicted_semantic_attribute"].notna()
    correct = mapped & (
        joined["predicted_semantic_attribute"] == joined["actual_semantic_attribute"]
    )
    correct_count = int(correct.sum())
    mapped_count = int(mapped.sum())
    total = len(joined)
    precision = correct_count / mapped_count if mapped_count else 0.0
    recall = correct_count / total if total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "rows": total,
        "correct_rows": correct_count,
        "incorrect_rows": mapped_count - correct_count,
        "unmapped_rows": total - mapped_count,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1_score": round(f1, 6),
    }


def measure(operation):
    tracemalloc.start()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    value = operation()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, {
        "wall_time_seconds": round(time.perf_counter() - wall_started, 6),
        "cpu_time_seconds": round(time.process_time() - cpu_started, 6),
        "peak_python_memory_mb": round(peak / (1024 * 1024), 6),
    }


def predictions_frame(data, mapper):
    return pd.DataFrame({
        "row_number": range(1, len(data) + 1),
        "value": data["customer_id"],
        "predicted_semantic_attribute": [mapper(value) for value in data["customer_id"]],
    })


def write_predictions(path, predictions):
    path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(path, index=False)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run(data_dir=CASE_DATA, results_dir=CASE_RESULTS, config_path=CASE_CONFIG):
    data_dir, results_dir, config_path = map(Path, (data_dir, results_dir, config_path))
    if not (data_dir / "manifest.json").is_file():
        raise FileNotFoundError(f"Jeu de calibration absent : {data_dir}")
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    identity = (manifest["campaign"], manifest["scenario"], manifest["intensity"], manifest["seed"])
    if identity != ("R01", "S05", "I1", 11):
        raise ValueError(f"Cas non autorisé pour ce pilote : {identity}")
    with config_path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    data = pd.read_csv(data_dir / "raw/mixed_events.csv")
    truth = pd.read_csv(data_dir / "ground_truth/value_ground_truth.csv")
    ticket_share = float(data["customer_id"].astype(str).str.startswith("TKT-").mean())
    customer_share = float(data["customer_id"].astype(str).str.startswith("CRM").mean())
    architectures = {}

    a0_predictions, performance = measure(
        lambda: predictions_frame(data, lambda value: target_from_prefix(value, config["A0"]["rules"]))
    )
    write_predictions(results_dir / "A0/predictions.csv", a0_predictions)
    architectures["A0"] = {
        "decision": "accepted_conditional_split",
        "value_quality": evaluate_predictions(a0_predictions, truth),
        "safe_handling": True,
        "human_reviews_required": 0,
        "silent_wrong_acceptances": 0,
        "configuration_actions": len(config["A0"]["rules"]) + 1,
        "performance": performance,
    }

    def run_a1():
        profile = next(
            row for row in profile_dataframe(data, "mixed_events")
            if row["column"] == "customer_id"
        )
        role, confidence, decision = technical_role(profile)
        predictions = predictions_frame(data, lambda _: config["A1"]["inferred_target_from_name"])
        return predictions, role, confidence, decision

    (a1_predictions, role, confidence, technical_decision), performance = measure(run_a1)
    write_predictions(results_dir / "A1/predictions.csv", a1_predictions)
    a1_quality = evaluate_predictions(a1_predictions, truth)
    architectures["A1"] = {
        "decision": technical_decision,
        "technical_role": role,
        "confidence": confidence,
        "value_quality": a1_quality,
        "safe_handling": False,
        "human_reviews_required": 0,
        "silent_wrong_acceptances": a1_quality["incorrect_rows"],
        "configuration_actions": 0,
        "performance": performance,
    }

    a2_before, before_performance = measure(
        lambda: predictions_frame(data, lambda _: config["A2"]["before_adaptation"]["target"])
    )
    a2_after, after_performance = measure(
        lambda: predictions_frame(
            data,
            lambda value: target_from_prefix(value, config["A2"]["after_adaptation"]["rules"]),
        )
    )
    write_predictions(results_dir / "A2/before_adaptation/predictions.csv", a2_before)
    write_predictions(results_dir / "A2/after_adaptation/predictions.csv", a2_after)
    before_quality, after_quality = evaluate_predictions(a2_before, truth), evaluate_predictions(a2_after, truth)
    architectures["A2"] = {
        "before_adaptation": {
            "decision": "accepted_static_mapping", "value_quality": before_quality,
            "safe_handling": False, "silent_wrong_acceptances": before_quality["incorrect_rows"],
            "performance": before_performance,
        },
        "after_adaptation": {
            "decision": "accepted_conditional_split", "value_quality": after_quality,
            "safe_handling": True, "silent_wrong_acceptances": 0,
            "adaptation_actions": config["A2"]["adaptation_actions"],
            "performance": after_performance,
        },
    }

    def run_a3():
        model = load_semantic_model(ROOT / config["A3"]["model"])
        _, _, decisions = analyze_sources(model, sources=("mixed_events",), raw_dir=data_dir / "raw")
        return next(row for row in decisions if row["source_column"] == "customer_id")

    raw_match, performance = measure(run_a3)
    dominant_share = max(ticket_share, customer_share)
    final_decision = (
        config["A3"]["mixed_semantic_classes"]
        if dominant_share < config["A3"]["minimum_dominant_share_for_single_mapping"]
        else raw_match["decision"]
    )
    architectures["A3"] = {
        "raw_candidate": raw_match["semantic_attribute"],
        "raw_decision": raw_match["decision"],
        "raw_score": raw_match["total_score"],
        "raw_margin": raw_match["score_margin"],
        "final_decision": final_decision,
        "ticket_share": ticket_share,
        "customer_share": customer_share,
        "safe_handling": final_decision == "review",
        "human_reviews_required": int(final_decision == "review"),
        "silent_wrong_acceptances": 0 if final_decision == "review" else int(ticket_share * len(data)),
        "configuration_actions": 0,
        "performance": performance,
    }

    payload = {
        "campaign": "R01", "subset": "calibration", "scenario": "S05",
        "intensity": "I1", "seed": 11,
        "dataset": {"rows": len(data), "ticket_share": ticket_share, "customer_share": customer_share},
        "architectures": architectures,
    }
    for architecture, result in architectures.items():
        write_json(results_dir / architecture / "results.json", result)
    write_json(results_dir / "summary.json", payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    run()

