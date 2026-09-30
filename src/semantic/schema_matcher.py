import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from src.semantic.model_loader import load_semantic_model
from src.semantic.profiler import profile_csv


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results" / "semantic"


def normalize_label(value):
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _name_score(column, attribute_name, attribute):
    source_name = normalize_label(column)
    candidates = [attribute_name, *attribute.get("synonyms", [])]
    return max(
        SequenceMatcher(None, source_name, normalize_label(candidate)).ratio()
        for candidate in candidates
    )


def _type_score(inferred_type, expected_type):
    if inferred_type == expected_type:
        return 1.0
    if {inferred_type, expected_type} <= {"integer", "decimal"}:
        return 0.8
    return 0.0


def _base_value_score(profile, attribute):
    expected_format = attribute.get("format")
    if expected_format:
        return 1.0 if profile["detected_format"] == expected_format else 0.0

    semantic_role = attribute.get("semantic_role")
    if semantic_role == "identifier":
        return profile["unique_ratio"]
    if semantic_role == "foreign_key":
        return 1.0 if profile["unique_ratio"] < 0.95 else 0.75

    return 1.0 if _type_score(profile["inferred_type"], attribute["type"]) else 0.0


def _semantic_attributes(model):
    for concept_name, concept in model["concepts"].items():
        for attribute_name, attribute in concept["attributes"].items():
            yield concept_name, attribute_name, attribute


def infer_source_concept(profiles, model):
    """Infer the row-level concept from its most unique identifier column."""
    scores = {concept_name: 0.0 for concept_name in model["concepts"]}
    for profile in profiles:
        column = normalize_label(profile["column"])
        for concept_name, concept in model["concepts"].items():
            for attribute_name, attribute in concept["attributes"].items():
                if attribute.get("semantic_role") != "identifier":
                    continue
                aliases = [attribute_name, *attribute.get("synonyms", [])]
                if column in {normalize_label(alias) for alias in aliases}:
                    scores[concept_name] = max(
                        scores[concept_name], profile["unique_ratio"]
                    )
    return max(scores, key=scores.get) if any(scores.values()) else None


def score_candidate(
    profile, concept_name, attribute_name, attribute, source_concept, weights
):
    name_score = _name_score(profile["column"], attribute_name, attribute)
    type_score = _type_score(profile["inferred_type"], attribute["type"])
    base_value_score = _base_value_score(profile, attribute)
    concept_affinity = 1.0 if concept_name == source_concept else 0.7
    value_score = 0.9 * base_value_score + 0.1 * concept_affinity
    total_score = (
        weights["name"] * name_score
        + weights["type"] * type_score
        + weights["value"] * value_score
    )
    return {
        "candidate": f"{concept_name}.{attribute_name}",
        "name_score": round(name_score, 6),
        "type_score": round(type_score, 6),
        "value_score": round(value_score, 6),
        "total_score": round(total_score, 6),
    }


def match_profiles(profiles, model):
    weights = model["matching_policy"]["weights"]
    by_source = {}
    for profile in profiles:
        by_source.setdefault(profile["source"], []).append(profile)

    matches = []
    for source, source_profiles in by_source.items():
        source_concept = infer_source_concept(source_profiles, model)
        for profile in source_profiles:
            candidates = [
                score_candidate(
                    profile,
                    concept_name,
                    attribute_name,
                    attribute,
                    source_concept,
                    weights,
                )
                for concept_name, attribute_name, attribute in _semantic_attributes(model)
            ]
            candidates.sort(key=lambda item: (-item["total_score"], item["candidate"]))
            best = candidates[0]
            second = candidates[1]
            matches.append(
                {
                    "source": source,
                    "source_concept": source_concept,
                    "source_column": profile["column"],
                    "inferred_type": profile["inferred_type"],
                    "detected_format": profile["detected_format"] or "",
                    "semantic_attribute": best["candidate"],
                    "name_score": best["name_score"],
                    "type_score": best["type_score"],
                    "value_score": best["value_score"],
                    "total_score": best["total_score"],
                    "second_candidate": second["candidate"],
                    "second_score": second["total_score"],
                    "score_margin": round(
                        best["total_score"] - second["total_score"], 6
                    ),
                }
            )
    return matches


def decide_match(match, thresholds):
    score = match["total_score"]
    margin = match["score_margin"]
    if score < thresholds["review_score"]:
        return "rejected", (
            f"Score insuffisant : {score:.3f} < "
            f"{thresholds['review_score']:.3f}"
        )
    if (
        score >= thresholds["auto_accept_score"]
        and margin >= thresholds["auto_accept_margin"]
    ):
        return "accepted", "Score et marge suffisants"

    reasons = []
    if score < thresholds["auto_accept_score"]:
        reasons.append(
            f"score {score:.3f} < {thresholds['auto_accept_score']:.3f}"
        )
    if margin < thresholds["auto_accept_margin"]:
        reasons.append(
            f"marge {margin:.3f} < {thresholds['auto_accept_margin']:.3f}"
        )
    return "review", "Validation requise : " + " ; ".join(reasons)


def apply_confidence_policy(matches, model):
    thresholds = model["matching_policy"]["thresholds"]
    decisions = []
    for match in matches:
        decision, reason = decide_match(match, thresholds)
        decisions.append({**match, "decision": decision, "decision_reason": reason})
    return decisions


def confidence_metrics(decisions, model):
    total = len(decisions)
    counts = {
        decision: sum(row["decision"] == decision for row in decisions)
        for decision in ("accepted", "review", "rejected")
    }
    return {
        "matching_policy": model["matching_policy"],
        "total_columns": total,
        "accepted_mappings": counts["accepted"],
        "mappings_requiring_review": counts["review"],
        "rejected_mappings": counts["rejected"],
        "human_interventions_required": counts["review"],
        "automation_rate": round(counts["accepted"] / total, 6) if total else 0.0,
        "average_total_score": round(
            sum(row["total_score"] for row in decisions) / total, 6
        ) if total else 0.0,
        "average_score_margin": round(
            sum(row["score_margin"] for row in decisions) / total, 6
        ) if total else 0.0,
    }


def analyze_sources(
    model=None, sources=("crm", "support", "finance"), raw_dir=RAW
):
    model = model or load_semantic_model()
    raw_dir = Path(raw_dir)
    profiles = []
    for source in sources:
        profiles.extend(profile_csv(raw_dir / f"{source}.csv", source))
    matches = match_profiles(profiles, model)
    decisions = apply_confidence_policy(matches, model)
    return profiles, matches, decisions


def run():
    model = load_semantic_model()
    profiles, matches, decisions = analyze_sources(model)

    RESULTS.mkdir(parents=True, exist_ok=True)
    profiles_path = RESULTS / "schema_profiles.json"
    matches_path = RESULTS / "semantic_schema_matches.csv"
    decisions_path = RESULTS / "semantic_schema_decisions.csv"
    review_path = RESULTS / "schema_review_queue.csv"
    metrics_path = RESULTS / "schema_confidence_metrics.json"
    profiles_path.write_text(
        json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with matches_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(matches[0]))
        writer.writeheader()
        writer.writerows(matches)
    with decisions_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    review_queue = [row for row in decisions if row["decision"] == "review"]
    with review_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(review_queue)
    metrics_path.write_text(
        json.dumps(confidence_metrics(decisions, model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Profiled columns: {len(profiles)}")
    print(f"Schema matches: {len(matches)}")
    print(f"Profiles: {profiles_path}")
    print(f"Matches: {matches_path}")
    print(f"Decisions: {decisions_path}")
    print(f"Review queue: {review_path}")
    print(f"Confidence metrics: {metrics_path}")


if __name__ == "__main__":
    run()
