import csv
import json
import time
from pathlib import Path

import pandas as pd
import yaml

from src.evaluation.evaluate_baseline import (
    GROUND_TRUTH,
    evaluate_entity_rows,
    read_csv,
    write_errors,
)
from src.semantic.model_loader import load_semantic_model
from src.semantic.schema_matcher import analyze_sources
from src.semantic.transformer import build_customer_view, merge_customer_views


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "output"
RESULTS = ROOT / "results" / "semantic" / "pipeline"
VALIDATIONS = ROOT / "semantic" / "human_validations.yaml"


def load_human_validations(path=VALIDATIONS):
    with Path(path).open(encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}
    validations = content.get("validations", [])
    return {
        (row["source"], row["source_column"]): row
        for row in validations
        if row.get("status") == "approved"
    }


def resolve_schema_mappings(decisions, validations):
    mappings = {}
    unresolved = []
    for row in decisions:
        key = (row["source"], row["source_column"])
        if row["decision"] == "accepted":
            mappings[key] = row["semantic_attribute"]
        elif row["decision"] == "review":
            validation = validations.get(key)
            if not validation:
                unresolved.append(key)
            elif validation["semantic_attribute"] != row["semantic_attribute"]:
                raise ValueError(
                    f"La validation de {key} ne correspond pas au candidat proposé."
                )
            else:
                mappings[key] = validation["semantic_attribute"]
    if unresolved:
        raise ValueError(f"Mappings encore en attente de validation : {unresolved}")
    return mappings


def mappings_for_source(all_mappings, source):
    return {
        column: semantic_attribute
        for (mapped_source, column), semantic_attribute in all_mappings.items()
        if mapped_source == source
    }


def run(
    run_evaluation=True,
    raw_dir=RAW,
    output_path=None,
    results_dir=RESULTS,
    ground_truth_path=GROUND_TRUTH,
    validations_path=VALIDATIONS,
):
    started_at = time.perf_counter()
    trace = []
    raw_dir = Path(raw_dir)
    results_dir = Path(results_dir)
    output_path = Path(output_path) if output_path else OUTPUT / "unified_customer_semantic.csv"
    results_dir.mkdir(parents=True, exist_ok=True)

    step_started = time.perf_counter()
    model = load_semantic_model()
    source_names = tuple(sorted(path.stem for path in raw_dir.glob("*.csv")))
    raw_frames = {
        source: pd.read_csv(raw_dir / f"{source}.csv") for source in source_names
    }
    trace.append(
        {
            "step": "load_sources_and_model",
            "duration_seconds": round(time.perf_counter() - step_started, 6),
            "rows": {source: len(frame) for source, frame in raw_frames.items()},
        }
    )

    step_started = time.perf_counter()
    profiles, matches, decisions = analyze_sources(
        model, sources=source_names, raw_dir=raw_dir
    )
    decisions_path = results_dir / "schema_decisions.csv"
    with decisions_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    validations = load_human_validations(validations_path)
    mappings = resolve_schema_mappings(decisions, validations)
    trace.append(
        {
            "step": "profile_match_and_decide",
            "duration_seconds": round(time.perf_counter() - step_started, 6),
            "profiled_columns": len(profiles),
            "accepted_automatically": sum(
                row["decision"] == "accepted" for row in decisions
            ),
            "human_validations": len(validations),
        }
    )

    step_started = time.perf_counter()
    source_concepts = {
        row["source"]: row["source_concept"] for row in decisions
    }
    customer_views = {
        source: build_customer_view(
            frame,
            source_concepts[source],
            mappings_for_source(mappings, source),
            model,
        )
        for source, frame in raw_frames.items()
    }
    trace.append(
        {
            "step": "semantic_transformations_and_aggregations",
            "duration_seconds": round(time.perf_counter() - step_started, 6),
            "customer_level_rows": {
                source: len(frame) for source, frame in customer_views.items()
            },
        }
    )

    step_started = time.perf_counter()
    unified = merge_customer_views(
        customer_views["crm"],
        customer_views["support"],
        customer_views["finance"],
        additional_views={
            source: view
            for source, view in customer_views.items()
            if source not in {"crm", "support", "finance"}
        },
    )
    trace.append(
        {
            "step": "entity_matching",
            "duration_seconds": round(time.perf_counter() - step_started, 6),
            "rule": "exact normalized email; missing values are never comparable",
            "output_rows": len(unified),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    unified.to_csv(output_path, index=False)

    pipeline_elapsed = time.perf_counter() - started_at

    evaluation_path = results_dir / "semantic_evaluation.json"
    errors_path = results_dir / "semantic_matching_errors.csv"
    evaluation = None
    if run_evaluation:
        step_started = time.perf_counter()
        predicted_rows = read_csv(output_path)
        truth_rows = read_csv(ground_truth_path)
        evaluation, errors = evaluate_entity_rows(truth_rows, predicted_rows)
        evaluation["evaluation_time_seconds"] = round(
            time.perf_counter() - step_started, 6
        )
        evaluation_path.write_text(
            json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        write_errors(errors_path, errors)

    metrics = {
        "pipeline": "semantic_assisted",
        "execution_time_seconds": round(pipeline_elapsed, 6),
        "automatic_schema_mappings": sum(
            row["decision"] == "accepted" for row in decisions
        ),
        "human_schema_validations": len(validations),
        "rejected_schema_mappings": sum(
            row["decision"] == "rejected" for row in decisions
        ),
        "declarative_derived_attributes": len(model["derived_attributes"]),
        "output_rows": int(len(unified)),
        "output_columns": int(len(unified.columns)),
    }
    if evaluation:
        metrics.update(
            {
                "entity_precision": evaluation["overall"]["precision"],
                "entity_recall": evaluation["overall"]["recall"],
                "entity_f1_score": evaluation["overall"]["f1_score"],
            }
        )
    metrics_path = results_dir / "semantic_pipeline_metrics.json"
    trace_path = results_dir / "execution_trace.json"
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    trace_path.write_text(
        json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"\nOutput: {output_path}")
    if run_evaluation:
        print(f"Evaluation: {evaluation_path}")
        print(f"Errors: {errors_path}")
    print(f"Trace: {trace_path}")


if __name__ == "__main__":
    run()
