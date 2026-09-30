import pandas as pd
import pytest

from src.declarative.model_loader import load_declarative_model
from src.declarative.transformer import (
    DeclarativeTransformationError,
    build_source_view,
    merge_source_views,
)


def test_a2_builds_crm_view_from_declared_rules():
    model = load_declarative_model()
    source = pd.DataFrame({
        "client_id": ["CRM1"],
        "first_name": ["Jean"],
        "last_name": ["Dupont"],
        "email": [" JEAN@EXAMPLE.COM "],
        "country": ["FR"],
        "created_at": ["2025-01-02"],
    })

    result = build_source_view(source, "crm", model)

    assert result.loc[0, "source_identifier"] == "CRM1"
    assert result.loc[0, "full_name"] == "Jean Dupont"
    assert result.loc[0, "email"] == "jean@example.com"
    assert result.loc[0, "country"] == "France"


def test_a2_aggregates_support_at_customer_granularity():
    model = load_declarative_model()
    source = pd.DataFrame({
        "ticket_id": ["T1", "T2"],
        "customer_ref": ["SUP1", "SUP1"],
        "full_name": ["Jean Dupont", "Jean Dupont"],
        "mail": ["j@example.com", "j@example.com"],
        "country_name": ["France", "France"],
        "created_at": ["2025-02-02", "2025-02-01"],
    })

    result = build_source_view(source, "support", model)

    assert len(result) == 1
    assert result.loc[0, "ticket_count"] == 2
    assert result.loc[0, "created_at"] == "2025-02-01"


def test_a2_fails_when_a_predefined_column_is_renamed():
    model = load_declarative_model()
    source = pd.DataFrame(columns=[
        "ticket_id", "customer_ref", "full_name", "customer_email_address",
        "country_name", "created_at",
    ])

    with pytest.raises(DeclarativeTransformationError, match="mail"):
        build_source_view(source, "support", model)


def test_a2_merges_exact_emails_but_never_missing_emails():
    model = load_declarative_model()
    crm = pd.DataFrame({
        "source_identifier": ["CRM1", "CRM2"],
        "email": ["same@example.com", pd.NA],
        "full_name": ["Same", "Missing CRM"],
    })
    support = pd.DataFrame({
        "source_identifier": ["SUP1", "SUP2"],
        "email": ["same@example.com", pd.NA],
        "full_name": ["Same", "Missing Support"],
    })

    result = merge_source_views({"crm": crm, "support": support}, model)

    assert len(result) == 3
    matched = result[result["email_norm"] == "same@example.com"].iloc[0]
    assert matched["crm_client_id"] == "CRM1"
    assert matched["support_customer_ref"] == "SUP1"
