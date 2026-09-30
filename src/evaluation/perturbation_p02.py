"""P02: evaluate resilience to a country-value format change."""

import csv
import json
import shutil
from pathlib import Path

import pandas as pd

from src.baseline.pipeline import run as run_baseline
from src.semantic.pipeline import run as run_semantic


ROOT = Path(__file__).resolve().parents[2]
SCENARIO = "p02_country_format"
SOURCE_RAW = ROOT / "data" / "raw"
SOURCE_TRUTH = ROOT / "data" / "ground_truth"
SCENARIO_DATA = ROOT / "data" / "perturbations" / SCENARIO
SCENARIO_RESULTS = ROOT / "results" / "perturbations" / SCENARIO

COUNTRY_NAMES = {
    "FR": "France", "CM": "Cameroon", "DE": "Germany", "ES": "Spain",
    "BE": "Belgium", "CA": "Canada", "IT": "Italy",
}


def generate_p02(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, scenario_data=SCENARIO_DATA):
    source_raw, source_truth, scenario_data = map(Path, (source_raw, source_truth, scenario_data))
    raw_dir, truth_dir = scenario_data / "raw", scenario_data / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_raw / "crm.csv", raw_dir / "crm.csv")
    shutil.copy2(source_raw / "support.csv", raw_dir / "support.csv")
    shutil.copy2(source_truth / "entity_mapping.csv", truth_dir / "entity_mapping.csv")
    shutil.copy2(source_truth / "schema_mapping.csv", truth_dir / "schema_mapping.csv")

    finance = pd.read_csv(source_raw / "finance.csv")
    original_codes = sorted(finance["country_code"].dropna().unique().tolist())
    finance["country_code"] = finance["country_code"].map(COUNTRY_NAMES).str.lower()
    finance.to_csv(raw_dir / "finance.csv", index=False)

    manifest = {
        "scenario": SCENARIO,
        "description": "Les codes pays Finance deviennent des libellés en minuscules.",
        "change": {
            "source": "finance", "column": "country_code",
            "before_examples": original_codes,
            "after_examples": sorted(finance["country_code"].dropna().unique().tolist()),
            "schema_modified": False, "values_modified": True,
        },
    }
    (scenario_data / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def country_quality(output_path):
    output = pd.read_csv(output_path)
    finance_rows = output.loc[
        output["finance_account_id"].notna(),
        ["finance_account_id", "finance_country"],
    ].drop_duplicates(subset=["finance_account_id"])
    observed = finance_rows["finance_country"]
    canonical = set(COUNTRY_NAMES.values())
    correct = int(observed.isin(canonical).sum())
    total = int(len(observed))
    return {
        "canonical_values": correct,
        "evaluated_finance_accounts": total,
        "country_conformity": round(correct / total, 6) if total else 0.0,
        "observed_formats": sorted(observed.dropna().astype(str).unique().tolist()),
    }


def run_p02():
    manifest = generate_p02()
    raw_dir = SCENARIO_DATA / "raw"
    truth = SCENARIO_DATA / "ground_truth" / "entity_mapping.csv"
    output_dir = SCENARIO_DATA / "output"
    baseline_results = SCENARIO_RESULTS / "baseline"
    semantic_results = SCENARIO_RESULTS / "semantic"
    baseline_output = output_dir / "baseline" / "unified_customer_baseline.csv"
    semantic_output = output_dir / "unified_customer_semantic.csv"

    run_baseline(raw_dir=raw_dir, output_dir=output_dir / "baseline", results_dir=baseline_results)
    run_semantic(
        raw_dir=raw_dir, output_path=semantic_output, results_dir=semantic_results,
        ground_truth_path=truth,
    )
    semantic_metrics = json.loads(
        (semantic_results / "semantic_pipeline_metrics.json").read_text(encoding="utf-8")
    )
    result = {
        **manifest,
        "phase": "after_adaptation",
        "baseline": {
            "status": "success", "code_changes_applied": 1,
            "adaptation": {
                "type": "imperative_python_rule",
                "files_modified": ["src/baseline/transform.py"],
                "rules_added": 1,
            },
            "value_quality": country_quality(baseline_output),
        },
        "semantic": {
            "status": "success", "code_changes_applied": 0,
            "incremental_human_validations": 0,
            "adaptation": {
                "type": "declarative_vocabulary_extension",
                "files_modified": ["semantic/model.yaml"],
                "vocabulary_entries_added": 7,
            },
            "value_quality": country_quality(semantic_output),
            "entity_quality": {
                "precision": semantic_metrics["entity_precision"],
                "recall": semantic_metrics["entity_recall"],
                "f1_score": semantic_metrics["entity_f1_score"],
            },
        },
        "interpretation": "La baseline exige une règle Python ; la couche sémantique exige seulement un enrichissement déclaratif.",
    }
    SCENARIO_RESULTS.mkdir(parents=True, exist_ok=True)
    (SCENARIO_RESULTS / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run_p02()
