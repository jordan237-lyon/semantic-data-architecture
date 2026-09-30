import csv
from pathlib import Path

from src.semantic.model_loader import load_semantic_model
from src.semantic.profiler import profile_csv
from src.semantic.schema_matcher import (
    confidence_metrics,
    apply_confidence_policy,
    decide_match,
    infer_source_concept,
    match_profiles,
)


ROOT = Path(__file__).resolve().parents[1]


def profile(column, inferred_type="string", detected_format=None, unique_ratio=1.0):
    return {
        "source": "support",
        "column": column,
        "inferred_type": inferred_type,
        "detected_format": detected_format,
        "unique_ratio": unique_ratio,
    }


def test_infers_support_ticket_as_source_concept():
    model = load_semantic_model()
    profiles = [
        profile("ticket_id", unique_ratio=1.0),
        profile("customer_ref", unique_ratio=0.2),
    ]

    assert infer_source_concept(profiles, model) == "SupportTicket"


def test_matches_email_from_name_type_and_values():
    model = load_semantic_model()
    profiles = [
        profile("ticket_id"),
        profile("mail", detected_format="email", unique_ratio=0.8),
    ]

    matches = match_profiles(profiles, model)
    email_match = next(item for item in matches if item["source_column"] == "mail")

    assert email_match["semantic_attribute"] == "Customer.email"
    assert email_match["total_score"] > 0.95


def test_confidence_metrics_returns_automation_counts():
    model = load_semantic_model()
    decisions = [
        {"decision": "accepted", "total_score": 0.9, "score_margin": 0.2},
        {"decision": "review", "total_score": 0.7, "score_margin": 0.05},
    ]

    metrics = confidence_metrics(decisions, model)

    assert metrics["accepted_mappings"] == 1
    assert metrics["mappings_requiring_review"] == 1
    assert metrics["automation_rate"] == 0.5


def test_uses_repetition_to_distinguish_foreign_key_from_identifier():
    model = load_semantic_model()
    profiles = [
        profile("ticket_id", unique_ratio=1.0),
        profile("customer_ref", unique_ratio=0.2),
    ]

    matches = match_profiles(profiles, model)
    reference_match = next(
        item for item in matches if item["source_column"] == "customer_ref"
    )

    assert (
        reference_match["semantic_attribute"]
        == "SupportTicket.customer_reference"
    )


def test_project_sources_match_the_schema_ground_truth():
    model = load_semantic_model()
    profiles = []
    for source in ("crm", "support", "finance"):
        profiles.extend(profile_csv(ROOT / "data" / "raw" / f"{source}.csv", source))
    predicted = {
        (row["source"], row["source_column"]): row["semantic_attribute"]
        for row in match_profiles(profiles, model)
    }
    with (ROOT / "data" / "ground_truth" / "schema_mapping.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        expected = {
            (row["source"], row["source_column"]): row["semantic_attribute"]
            for row in csv.DictReader(stream)
        }

    assert predicted == expected


def test_confidence_policy_accepts_reviews_and_rejects():
    thresholds = {
        "auto_accept_score": 0.85,
        "auto_accept_margin": 0.10,
        "review_score": 0.60,
    }

    assert decide_match(
        {"total_score": 0.95, "score_margin": 0.20}, thresholds
    )[0] == "accepted"
    assert decide_match(
        {"total_score": 0.95, "score_margin": 0.02}, thresholds
    )[0] == "review"
    assert decide_match(
        {"total_score": 0.40, "score_margin": 0.20}, thresholds
    )[0] == "rejected"


def test_project_ambiguous_dates_require_review():
    model = load_semantic_model()
    profiles = []
    for source in ("crm", "support", "finance"):
        profiles.extend(profile_csv(ROOT / "data" / "raw" / f"{source}.csv", source))

    decisions = apply_confidence_policy(match_profiles(profiles, model), model)
    review_columns = {
        (row["source"], row["source_column"])
        for row in decisions
        if row["decision"] == "review"
    }

    assert review_columns == {("crm", "created_at"), ("support", "created_at")}
