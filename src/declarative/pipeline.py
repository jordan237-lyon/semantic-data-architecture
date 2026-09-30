"""A2 pipeline: predefined declarative mappings, without adaptive matching."""

import json
import time
from pathlib import Path

import pandas as pd

from src.declarative.model_loader import DEFAULT_MODEL_PATH, load_declarative_model
from src.declarative.transformer import (
    DeclarativeTransformationError,
    build_source_view,
    merge_source_views,
)
from src.evaluation.evaluate_baseline import (
    GROUND_TRUTH,
    evaluate_entity_rows,
    read_csv,
    write_errors,
)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "output" / "unified_customer_a2.csv"
RESULTS = ROOT / "results" / "benchmark_v2" / "P00" / "A2"


def discover_declared_sources(raw_dir, model):
    discovered = {path.stem: path for path in Path(raw_dir).glob("*.csv")}
    declared = set(model["sources"])
    missing = sorted(declared - set(discovered))
    unknown = sorted(set(discovered) - declared)
    if missing:
        raise DeclarativeTransformationError(
            "Sources A2 déclarées mais absentes : " + ", ".join(missing)
        )
    if unknown:
        raise DeclarativeTransformationError(
            "Sources découvertes mais non déclarées dans A2 : " + ", ".join(unknown)
        )
    return {name: discovered[name] for name in model["sources"]}


def run(
    raw_dir=RAW,
    output_path=OUTPUT,
    results_dir=RESULTS,
    ground_truth_path=GROUND_TRUTH,
    model_path=DEFAULT_MODEL_PATH,
    run_evaluation=True,
):
    started = time.perf_counter()
    model = load_declarative_model(model_path)
    source_paths = discover_declared_sources(raw_dir, model)
    frames = {name: pd.read_csv(path) for name, path in source_paths.items()}
    views = {
        name: build_source_view(frame, name, model)
        for name, frame in frames.items()
    }
    unified = merge_source_views(views, model)

    output_path, results_dir = Path(output_path), Path(results_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    unified.to_csv(output_path, index=False)

    evaluation = None
    if run_evaluation:
        evaluation, errors = evaluate_entity_rows(
            read_csv(Path(ground_truth_path)), read_csv(output_path)
        )
        (results_dir / "evaluation.json").write_text(
            json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        write_errors(results_dir / "matching_errors.csv", errors)

    mappings = sum(len(source["mappings"]) for source in model["sources"].values())
    transformations = sum(
        len(mapping.get("transformations", []))
        for source in model["sources"].values()
        for mapping in source["mappings"].values()
    )
    metrics = {
        "architecture": "A2_declarative_semantic",
        "automatic_matching": False,
        "confidence_scoring": False,
        "declared_sources": list(model["sources"]),
        "declarative_schema_mappings": mappings,
        "declarative_transformations": transformations,
        "output_rows": len(unified),
        "output_columns": len(unified.columns),
        "entity_quality": evaluation["overall"] if evaluation else None,
        "execution_time_seconds": round(time.perf_counter() - started, 6),
    }
    (results_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return metrics


if __name__ == "__main__":
    run()
