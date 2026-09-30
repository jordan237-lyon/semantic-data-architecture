import pandas as pd
import pytest

from src.semantic.model_loader import load_semantic_model
from src.semantic.pipeline import resolve_schema_mappings
from src.semantic.transformer import build_customer_view, merge_customer_views


def test_support_aggregation_is_driven_by_semantic_model():
    model = load_semantic_model()
    source = pd.DataFrame(
        {
            "ticket_id": ["T1", "T2"],
            "customer_ref": ["SUP1", "SUP1"],
            "mail": [" CLIENT@EXAMPLE.COM ", " CLIENT@EXAMPLE.COM "],
            "full_name": ["CLIENT TEST", "CLIENT TEST"],
            "country_name": ["France", "France"],
        }
    )
    mappings = {
        "ticket_id": "SupportTicket.identifier",
        "customer_ref": "SupportTicket.customer_reference",
        "mail": "Customer.email",
        "full_name": "Customer.full_name",
        "country_name": "Customer.country",
    }

    result = build_customer_view(source, "SupportTicket", mappings, model)

    assert len(result) == 1
    assert result.loc[0, "ticket_count"] == 2
    assert result.loc[0, "email"] == "client@example.com"


def test_missing_emails_are_never_joined():
    crm = pd.DataFrame(
        [{"source_identifier": "CRM1", "full_name": "A", "email": pd.NA}]
    )
    support = pd.DataFrame(
        [
            {
                "source_identifier": "SUP1",
                "full_name": "B",
                "email": pd.NA,
                "ticket_count": 1,
            }
        ]
    )
    finance = pd.DataFrame(
        [
            {
                "source_identifier": "ACC1",
                "full_name": "C",
                "email": pd.NA,
                "revenue": 10.0,
            }
        ]
    )

    result = merge_customer_views(crm, support, finance)

    assert len(result) == 3
    assert not (
        result["crm_client_id"].notna()
        & result["support_customer_ref"].notna()
    ).any()
    assert not (
        result["support_customer_ref"].notna()
        & result["finance_account_id"].notna()
    ).any()


def test_review_mapping_requires_an_explicit_human_validation():
    decisions = [
        {
            "source": "crm",
            "source_column": "created_at",
            "semantic_attribute": "Customer.created_at",
            "decision": "review",
        }
    ]

    with pytest.raises(ValueError, match="attente de validation"):
        resolve_schema_mappings(decisions, {})


def test_approved_human_validation_resolves_review_mapping():
    decisions = [
        {
            "source": "crm",
            "source_column": "created_at",
            "semantic_attribute": "Customer.created_at",
            "decision": "review",
        }
    ]
    validations = {
        ("crm", "created_at"): {
            "semantic_attribute": "Customer.created_at",
            "status": "approved",
        }
    }

    assert resolve_schema_mappings(decisions, validations) == {
        ("crm", "created_at"): "Customer.created_at"
    }
