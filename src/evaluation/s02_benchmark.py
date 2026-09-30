"""Execute the frozen A0-A3 configurations on semantic scenario S02."""

import csv
import io
import json
import time
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd
import yaml

from src.declarative.pipeline import run as run_a2
from src.evaluation.evaluate_baseline import evaluate_entity_rows, extract_pairs, read_csv
from src.evaluation.metrics import evaluate_pairs
from src.metadata.pipeline import merge_views, run as run_a1
from src.semantic.model_loader import load_semantic_model
from src.semantic.schema_matcher import analyze_sources

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/semantic_scenarios/S02"
RESULTS = ROOT / "results/benchmark_v2/S02"
OUTPUTS = ROOT / "data/output/benchmark_v2/S02"
AMOUNT_TRUTH = {
    ("finance", "gross_amount"): "Transaction.amount",
    ("sales", "turnover_value"): "Transaction.amount",
}


def mapping_metrics(decisions):
    rows = [row for row in decisions if (row["source"], row["source_column"]) in AMOUNT_TRUTH]
    accepted = [row for row in rows if row["decision"] == "accepted"]
    correct = lambda row: row.get("semantic_attribute") == AMOUNT_TRUTH[(row["source"], row["source_column"])]
    accepted_correct = sum(correct(row) for row in accepted)
    correct_candidates = sum(correct(row) for row in rows)
    wrong_revenue = sum(
        row.get("semantic_attribute") == "Customer.revenue" and row["decision"] == "accepted"
        for row in rows
    )
    precision = accepted_correct / len(accepted) if accepted else 0.0
    recall = accepted_correct / len(AMOUNT_TRUTH)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "expected_mappings": 2,
        "accepted_correct": accepted_correct,
        "accepted_incorrect": len(accepted) - accepted_correct,
        "accepted_as_customer_revenue": wrong_revenue,
        "review_mappings": sum(row["decision"] == "review" for row in rows),
        "candidate_accuracy": round(correct_candidates / 2, 6),
        "coverage": round(len(accepted) / 2, 6),
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


def crm_sales_quality(output_path):
    truth, predicted = read_csv(DATA / "ground_truth/entity_mapping.csv"), read_csv(output_path)
    columns = ("crm_client_id", "sales_account_reference")
    return evaluate_pairs(extract_pairs(predicted, *columns), extract_pairs(truth, *columns))


def historical_quality(output_path):
    result, _ = evaluate_entity_rows(
        read_csv(DATA / "ground_truth/entity_mapping.csv"), read_csv(output_path)
    )
    return result["overall"]


def run_a0_manual():
    raw = {name: pd.read_csv(DATA / f"raw/{name}.csv") for name in ("crm", "support", "finance", "sales")}
    views = {
        "crm": pd.DataFrame({"crm_client_id": raw["crm"]["client_id"], "email": raw["crm"]["email"].str.strip().str.lower(), "source_row_count": 1}),
        "support": raw["support"].assign(email=raw["support"]["mail"].str.strip().str.lower()).groupby("customer_ref", as_index=False).agg(email=("email", "first"), source_row_count=("ticket_id", "size")).rename(columns={"customer_ref": "support_customer_ref"}),
        "finance": raw["finance"].assign(email=raw["finance"]["contact_email"].str.strip().str.lower()).groupby("account_id", as_index=False).agg(email=("email", "first"), source_row_count=("transaction_id", "size"), finance_revenue=("gross_amount", "sum")).rename(columns={"account_id": "finance_account_id"}),
        "sales": raw["sales"].assign(email=raw["sales"]["customer_email"].str.strip().str.lower()).groupby("account_reference", as_index=False).agg(email=("email", "first"), source_row_count=("sale_id", "size"), sales_revenue=("turnover_value", "sum")).rename(columns={"account_reference": "sales_account_reference"}),
    }
    unified = merge_views(views)
    output = OUTPUTS / "A0/unified_customer_a0.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    unified.to_csv(output, index=False)
    return output


def run():
    results = {}
    started = time.perf_counter()
    a0_output = run_a0_manual()
    with (ROOT / "config/benchmark_v2/S02/a0_manual_mappings.yaml").open(encoding="utf-8") as stream:
        rules = yaml.safe_load(stream)["rules"]
    a0_decisions = [
        {"source": rule["source"], "source_column": rule["source_column"], "semantic_attribute": rule["target"], "decision": "accepted", "confidence": "manual", "reason": "Règle manuelle explicite"}
        for rule in rules if rule["source_column"] in {"gross_amount", "turnover_value"}
    ]
    write_decisions(RESULTS / "A0/amount_decisions.csv", a0_decisions)
    results["A0"] = {"schema_quality": mapping_metrics(a0_decisions), "historical_entity_quality": historical_quality(a0_output), "crm_sales_quality": crm_sales_quality(a0_output), "manual_schema_rules": 6, "manual_aggregation_rules": 2, "execution_time_seconds": round(time.perf_counter() - started, 6)}

    started = time.perf_counter()
    with redirect_stdout(io.StringIO()):
        a1_metrics = run_a1(raw_dir=DATA / "raw", output_path=OUTPUTS / "A1/unified_customer_a1.csv", results_dir=RESULTS / "A1", ground_truth_path=DATA / "ground_truth/entity_mapping.csv")
    a1_decisions = [
        {"source": source, "source_column": column, "semantic_attribute": "", "decision": "review", "confidence": 0.8, "reason": "Mesure numérique sans concept métier ni granularité"}
        for source, column in (("finance", "gross_amount"), ("sales", "turnover_value"))
    ]
    write_decisions(RESULTS / "A1/amount_decisions.csv", a1_decisions)
    results["A1"] = {"schema_quality": mapping_metrics(a1_decisions), "historical_entity_quality": a1_metrics["entity_quality"], "crm_sales_quality": crm_sales_quality(OUTPUTS / "A1/unified_customer_a1.csv"), "human_reviews_required": 2, "execution_time_seconds": round(time.perf_counter() - started, 6)}

    started = time.perf_counter()
    a2_model_path = ROOT / "semantic/scenarios/a2_s02_model.yaml"
    with redirect_stdout(io.StringIO()):
        a2_metrics = run_a2(raw_dir=DATA / "raw", output_path=OUTPUTS / "A2/unified_customer_a2.csv", results_dir=RESULTS / "A2", ground_truth_path=DATA / "ground_truth/entity_mapping.csv", model_path=a2_model_path)
    a2_decisions = [
        {"source": source, "source_column": column, "semantic_attribute": "Transaction.amount", "decision": "accepted", "confidence": "declared", "reason": "Mapping YAML au niveau transaction"}
        for source, column in (("finance", "gross_amount"), ("sales", "turnover_value"))
    ]
    write_decisions(RESULTS / "A2/amount_decisions.csv", a2_decisions)
    results["A2"] = {"schema_quality": mapping_metrics(a2_decisions), "historical_entity_quality": a2_metrics["entity_quality"], "crm_sales_quality": crm_sales_quality(OUTPUTS / "A2/unified_customer_a2.csv"), "declarative_schema_mappings": 2, "execution_time_seconds": round(time.perf_counter() - started, 6)}

    started = time.perf_counter()
    a3_model = load_semantic_model(ROOT / "semantic/scenarios/a3_s02_model.yaml")
    _, _, decisions = analyze_sources(a3_model, sources=("crm", "support", "finance", "sales"), raw_dir=DATA / "raw")
    selected = [row for row in decisions if (row["source"], row["source_column"]) in AMOUNT_TRUTH]
    a3_decisions = [
        {"source": row["source"], "source_column": row["source_column"], "semantic_attribute": row["semantic_attribute"], "decision": row["decision"], "confidence": row["total_score"], "reason": row["decision_reason"]}
        for row in selected
    ]
    write_decisions(RESULTS / "A3/amount_decisions.csv", a3_decisions)
    results["A3"] = {"schema_quality": mapping_metrics(a3_decisions), "pipeline_status": "schema_analysis_only", "execution_time_seconds": round(time.perf_counter() - started, 6)}

    for architecture, result in results.items():
        path = RESULTS / architecture / "results.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "summary.json").write_text(json.dumps({"scenario": "S02", "architectures": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    run()
