import pytest

from app.services.scenarios import get_scenario, list_scenarios, list_sources, profile_scenario


def test_application_catalog_exposes_p00_and_semantic_scenarios():
    assert [scenario.identifier for scenario in list_scenarios()] == [
        "P00", "S01", "S02", "S03", "S04", "S05"
    ]


def test_p00_sources_are_read_without_modification():
    sources = list_sources("P00")

    assert {source.name for source in sources} == {"crm", "support", "finance"}
    assert all(source.row_count > 0 and source.column_count > 0 for source in sources)


def test_s05_profile_exposes_the_ambiguous_customer_id():
    profile = next(
        row for row in profile_scenario("S05")
        if row["source"] == "mixed_events" and row["column"] == "customer_id"
    )

    assert profile["inferred_type"] == "string"
    assert profile["unique_ratio"] == 1.0


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError, match="Scénario inconnu"):
        get_scenario("unknown")
