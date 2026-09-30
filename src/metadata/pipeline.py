"""A1 pipeline: automatic discovery and technical metadata only."""

import csv
import json
import re
import time
from pathlib import Path

import pandas as pd

from src.evaluation.evaluate_baseline import evaluate_entity_rows, read_csv, write_errors
from src.metadata.profiler import profile_dataframe


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
GROUND_TRUTH = ROOT / "data" / "ground_truth" / "entity_mapping.csv"
OUTPUT = ROOT / "data" / "output" / "unified_customer_a1.csv"
RESULTS = ROOT / "results" / "benchmark_v2" / "P00" / "A1"


def technical_role(profile):
    """Classify a column from technical evidence, without business concepts."""
    label = re.sub(r"[^a-z0-9]+", "_", profile["column"].lower()).strip("_")
    if profile["detected_format"] == "email":
        return "email", 1.0, "mapped"
    if profile["detected_format"] == "date":
        return "date", 0.95, "mapped"
    if profile["detected_format"] == "country_code":
        return "country_code", 0.95, "mapped"
    if label.endswith(("_id", "_ref", "_reference")) or label == "id":
        return "identifier", 0.85, "mapped"
    if profile["inferred_type"] in {"integer", "decimal"}:
        return "numeric_measure", 0.80, "mapped"
    return "unclassified_text", 0.50, "review"


def choose_email_column(profiles):
    candidates = [row for row in profiles if row["detected_format"] == "email"]
    if not candidates:
        return None
    return max(candidates, key=lambda row: (row["non_null_count"], row["unique_ratio"]))["column"]


def choose_entity_id_column(profiles):
    candidates = []
    for row in profiles:
        label = row["column"].lower()
        if label.endswith(("_id", "_ref", "_reference")) or label == "id":
            candidates.append(row)
    if not candidates:
        return None
    return min(candidates, key=lambda row: (row["unique_ratio"], row["column"]))["column"]


def build_technical_view(dataframe, source, profiles):
    email_column = choose_email_column(profiles)
    identifier_column = choose_entity_id_column(profiles)
    if not email_column or not identifier_column:
        raise ValueError(f"A1 cannot infer linkage columns for source {source}")
    working = pd.DataFrame({
        f"{source}_{identifier_column}": dataframe[identifier_column],
        "email": dataframe[email_column].astype("string").str.strip().str.lower(),
    })
    working.loc[working["email"] == "", "email"] = pd.NA
    return working.groupby(f"{source}_{identifier_column}", as_index=False).agg(
        email=("email", "first"),
        source_row_count=("email", "size"),
    )


def merge_views(views):
    prepared = []
    for source, view in views.items():
        current = view.rename(columns={
            "email": f"{source}_email",
            "source_row_count": f"{source}_row_count",
        }).copy()
        email_column = f"{source}_email"
        current["_match_key"] = current[email_column].astype("object")
        missing = current[email_column].isna()
        current.loc[missing, "_match_key"] = [
            f"__missing__:{source}:{index}" for index in current.index[missing]
        ]
        prepared.append((source, current))
    unified = prepared[0][1]
    for _, current in prepared[1:]:
        unified = unified.merge(current, on="_match_key", how="outer")
    email_columns = [f"{source}_email" for source in views]
    unified["email_norm"] = unified[email_columns[0]]
    for column in email_columns[1:]:
        unified["email_norm"] = unified["email_norm"].combine_first(unified[column])
    return unified.drop(columns=["_match_key", *email_columns])


def run(raw_dir=RAW, output_path=OUTPUT, results_dir=RESULTS, ground_truth_path=GROUND_TRUTH):
    started = time.perf_counter()
    raw_dir, output_path, results_dir = map(Path, (raw_dir, output_path, results_dir))
    source_paths = sorted(raw_dir.glob("*.csv"))
    frames = {path.stem: pd.read_csv(path) for path in source_paths}
    profiles = []
    by_source = {}
    for source, frame in frames.items():
        by_source[source] = profile_dataframe(frame, source)
        profiles.extend(by_source[source])
    mappings = []
    for profile in profiles:
        role, confidence, decision = technical_role(profile)
        mappings.append({
            "source": profile["source"], "source_column": profile["column"],
            "technical_role": role, "confidence": confidence, "decision": decision,
        })
    views = {
        source: build_technical_view(frame, source, by_source[source])
        for source, frame in frames.items()
    }
    unified = merge_views(views)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    unified.to_csv(output_path, index=False)
    (results_dir / "schema_profiles.json").write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (results_dir / "technical_mappings.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(mappings[0]))
        writer.writeheader()
        writer.writerows(mappings)

    evaluation, errors = evaluate_entity_rows(read_csv(Path(ground_truth_path)), read_csv(output_path))
    write_errors(results_dir / "matching_errors.csv", errors)
    metrics = {
        "architecture": "A1_technical_metadata",
        "semantic_model_used": False,
        "discovered_sources": list(frames),
        "profiled_columns": len(profiles),
        "mapped_technical_roles": sum(row["decision"] == "mapped" for row in mappings),
        "review_columns": sum(row["decision"] == "review" for row in mappings),
        "output_rows": len(unified),
        "entity_quality": evaluation["overall"],
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }
    (results_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return metrics


if __name__ == "__main__":
    run()
