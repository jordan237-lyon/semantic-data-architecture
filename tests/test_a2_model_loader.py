import copy

import pytest

from src.declarative.model_loader import (
    DeclarativeModelError,
    load_declarative_model,
    validate_declarative_model,
)


def test_a2_model_is_valid_and_non_adaptive():
    model = load_declarative_model()

    assert model["architecture"] == {
        "level": "A2",
        "mode": "declarative",
        "automatic_matching": False,
        "confidence_scoring": False,
    }
    assert set(model["sources"]) == {"crm", "support", "finance"}


def test_a2_rejects_automatic_matching():
    model = copy.deepcopy(load_declarative_model())
    model["architecture"]["automatic_matching"] = True

    with pytest.raises(DeclarativeModelError, match="interdit le matching"):
        validate_declarative_model(model)


def test_a2_rejects_unknown_canonical_target():
    model = copy.deepcopy(load_declarative_model())
    model["sources"]["crm"]["mappings"]["email"]["target"] = "unknown"

    with pytest.raises(DeclarativeModelError, match="Cible canonique inconnue"):
        validate_declarative_model(model)


def test_a2_p01_overlay_renames_only_the_declared_mapping():
    model = load_declarative_model("semantic/scenarios/a2_p01_model.yaml")
    mappings = model["sources"]["support"]["mappings"]

    assert "mail" not in mappings
    assert mappings["customer_email_address"] == {
        "target": "email",
        "transformations": ["trim", "lowercase"],
    }


def test_a2_p02_overlay_adds_only_country_vocabulary():
    base = load_declarative_model()
    adapted = load_declarative_model("semantic/scenarios/a2_p02_model.yaml")
    base_vocabulary = base["normalization_catalog"]["country_dictionary"]
    adapted_vocabulary = adapted["normalization_catalog"]["country_dictionary"]

    assert len(adapted_vocabulary) == len(base_vocabulary) + 7
    assert adapted_vocabulary["france"] == "France"
    assert "france" not in base_vocabulary


def test_a2_p03_overlay_replaces_composed_name_with_direct_mapping():
    model = load_declarative_model("semantic/scenarios/a2_p03_model.yaml")
    crm = model["sources"]["crm"]

    assert "first_name" not in crm["mappings"]
    assert "last_name" not in crm["mappings"]
    assert crm["mappings"]["customer_name"]["target"] == "full_name"
    assert "full_name" not in crm["derived_attributes"]


def test_a2_p05_overlay_declares_loyalty_without_changing_existing_sources():
    base = load_declarative_model()
    adapted = load_declarative_model("semantic/scenarios/a2_p05_model.yaml")

    assert set(adapted["sources"]) == {*base["sources"], "loyalty"}
    loyalty = adapted["sources"]["loyalty"]
    assert loyalty["entity_identifier"] == "member_id"
    assert len(loyalty["mappings"]) == 5
    assert loyalty["mappings"]["email_address"]["target"] == "email"


def test_a2_s01_declares_two_distinct_status_targets():
    model = load_declarative_model("semantic/scenarios/a2_s01_model.yaml")

    assert model["sources"]["crm"]["mappings"]["status"]["target"] == "customer_status"
    assert model["sources"]["support"]["mappings"]["status"]["target"] == "ticket_status"


def test_a2_s02_preserves_transaction_amount_before_aggregation():
    model = load_declarative_model("semantic/scenarios/a2_s02_model.yaml")

    assert model["sources"]["finance"]["mappings"]["gross_amount"]["target"] == "transaction_amount"
    assert model["sources"]["sales"]["mappings"]["turnover_value"]["target"] == "transaction_amount"
    assert model["sources"]["finance"]["aggregation"]["rules"]["transaction_amount"] == "sum"


def test_a2_s03_keeps_gross_and_net_revenue_separate():
    model = load_declarative_model("semantic/scenarios/a2_s03_model.yaml")

    assert model["sources"]["revenue_gross"]["mappings"]["gross_revenue"]["target"] == "gross_revenue"
    assert model["sources"]["revenue_net"]["mappings"]["net_revenue"]["target"] == "net_revenue"
    assert model["sources"]["revenue_gross"]["granularity"] == "customer_month"


def test_a2_s04_requires_two_declarative_versions_for_active():
    before = load_declarative_model("semantic/scenarios/a2_s04_before_model.yaml")
    after = load_declarative_model("semantic/scenarios/a2_s04_after_model.yaml")

    assert before["sources"]["customer_activity"]["mappings"]["active"]["target"] == "recently_active_90d"
    assert after["sources"]["customer_activity"]["mappings"]["active"]["target"] == "paying_contract_active"


def test_a2_s05_static_mapping_treats_mixed_customer_id_as_one_attribute():
    model = load_declarative_model("semantic/scenarios/a2_s05_model.yaml")
    source = model["sources"]["mixed_events"]

    assert source["mappings"]["customer_id"]["target"] == "customer_id"
    assert source["granularity"] == "event"
