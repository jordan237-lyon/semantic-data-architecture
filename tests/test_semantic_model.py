from copy import deepcopy
import csv
from pathlib import Path

import pytest

from src.semantic.model_loader import (
    SemanticModelError,
    load_semantic_model,
    validate_semantic_model,
)


ROOT = Path(__file__).resolve().parents[1]


def test_loads_the_project_semantic_model():
    model = load_semantic_model()

    assert model["canonical_entity"] == "Customer"
    assert set(model["concepts"]) == {"Customer", "SupportTicket", "Transaction"}
    assert (
        model["concepts"]["Customer"]["attributes"]["email"]["matching"][
            "nulls_are_comparable"
        ]
        is False
    )
    assert model["derived_attributes"]["Customer.revenue"]["aggregation"] == "sum"
    assert (
        model["concepts"]["SupportTicket"]["attributes"]["customer_reference"][
            "references"
        ]
        == "Customer.identifier"
    )
    assert (
        model["relations"][0]["target_attribute"]
        == "SupportTicket.customer_reference"
    )


def test_rejects_a_relation_to_an_unknown_concept():
    model = deepcopy(load_semantic_model())
    model["relations"][0]["target"] = "UnknownConcept"

    with pytest.raises(SemanticModelError, match="concept inconnu"):
        validate_semantic_model(model)


def test_rejects_matching_weights_that_do_not_sum_to_one():
    model = deepcopy(load_semantic_model())
    model["matching_policy"]["weights"]["name"] = 0.60

    with pytest.raises(SemanticModelError, match="somme des poids"):
        validate_semantic_model(model)


def test_rejects_an_ambiguous_synonym_within_a_concept():
    model = deepcopy(load_semantic_model())
    model["concepts"]["Customer"]["attributes"]["country"]["synonyms"].append(
        "email"
    )

    with pytest.raises(SemanticModelError, match="Synonyme ambigu"):
        validate_semantic_model(model)


def test_rejects_an_unknown_foreign_key_target():
    model = deepcopy(load_semantic_model())
    model["concepts"]["Transaction"]["attributes"]["account_reference"][
        "references"
    ] = "Customer.unknown"

    with pytest.raises(SemanticModelError, match="attribut inconnu"):
        validate_semantic_model(model)


def test_schema_ground_truth_uses_known_semantic_attributes():
    model = load_semantic_model()
    known_attributes = {
        f"{concept_name}.{attribute_name}"
        for concept_name, concept in model["concepts"].items()
        for attribute_name in concept["attributes"]
    }
    mapping_path = ROOT / "data" / "ground_truth" / "schema_mapping.csv"
    with mapping_path.open(newline="", encoding="utf-8") as stream:
        mappings = list(csv.DictReader(stream))

    assert len(mappings) == 19
    assert all(row["semantic_attribute"] in known_attributes for row in mappings)
    assert all(
        not row["references"] or row["references"] in known_attributes
        for row in mappings
    )


def test_s01_model_keeps_same_synonym_under_distinct_contexts():
    model = load_semantic_model(ROOT / "semantic/scenarios/a3_s01_model.yaml")

    customer_status = model["concepts"]["Customer"]["attributes"]["customer_status"]
    ticket_status = model["concepts"]["SupportTicket"]["attributes"]["ticket_status"]
    assert customer_status["synonyms"] == ["status"]
    assert ticket_status["synonyms"] == ["status"]
    assert customer_status["semantic_context"] != ticket_status["semantic_context"]


def test_s02_model_equates_amount_names_at_transaction_grain():
    model = load_semantic_model(ROOT / "semantic/scenarios/a3_s02_model.yaml")
    transaction = model["concepts"]["Transaction"]["attributes"]

    assert "gross_amount" in transaction["amount"]["synonyms"]
    assert "turnover_value" in transaction["amount"]["synonyms"]
    assert "sale_id" in transaction["identifier"]["synonyms"]


def test_s03_model_defines_competing_revenues_without_aliasing_them():
    model = load_semantic_model(ROOT / "semantic/scenarios/a3_s03_model.yaml")
    attributes = model["concepts"]["RevenueSnapshot"]["attributes"]

    assert attributes["gross_revenue"]["definition"] != attributes["net_revenue"]["definition"]
    assert attributes["gross_revenue"]["grain"] == "customer_month"
    assert attributes["net_revenue"]["unit"] == "EUR"


def test_s04_model_exposes_two_time_bound_meanings_for_active():
    model = load_semantic_model(ROOT / "semantic/scenarios/a3_s04_model.yaml")
    customer = model["concepts"]["Customer"]["attributes"]

    assert customer["recently_active_90d"]["synonyms"] == ["active"]
    assert customer["paying_contract_active"]["synonyms"] == ["active"]
    assert str(customer["recently_active_90d"]["valid_to"]) == "2025-06-30"
    assert str(customer["paying_contract_active"]["valid_from"]) == "2025-07-01"


def test_s05_model_exposes_customer_id_as_cross_concept_ambiguity():
    model = load_semantic_model(ROOT / "semantic/scenarios/a3_s05_model.yaml")

    assert "customer_id" in model["concepts"]["Customer"]["attributes"]["identifier"]["synonyms"]
    assert "customer_id" in model["concepts"]["SupportTicket"]["attributes"]["identifier"]["synonyms"]
