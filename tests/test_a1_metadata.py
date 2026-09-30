import pandas as pd

from src.metadata.campaign import loyalty_quality
from src.metadata.pipeline import (
    build_technical_view,
    choose_entity_id_column,
    merge_views,
    technical_role,
)
from src.metadata.profiler import profile_dataframe


def test_a1_infers_repeated_reference_as_entity_identifier():
    frame = pd.DataFrame({
        "ticket_id": ["T1", "T2", "T3"],
        "customer_ref": ["C1", "C1", "C2"],
        "mail": ["a@example.com", "a@example.com", "b@example.com"],
    })
    profiles = profile_dataframe(frame, "support")

    assert choose_entity_id_column(profiles) == "customer_ref"
    view = build_technical_view(frame, "support", profiles)
    assert len(view) == 2


def test_a1_does_not_join_missing_emails():
    crm = pd.DataFrame({"crm_client_id": ["C1"], "email": [pd.NA], "source_row_count": [1]})
    support = pd.DataFrame({"support_customer_ref": ["S1"], "email": [pd.NA], "source_row_count": [1]})

    result = merge_views({"crm": crm, "support": support})

    assert len(result) == 2


def test_a1_technical_roles_use_formats_not_business_vocabulary():
    profile = {
        "column": "contact", "detected_format": "email",
        "inferred_type": "string",
    }

    assert technical_role(profile) == ("email", 1.0, "mapped")


def test_loyalty_quality_evaluates_new_relation(tmp_path):
    truth = tmp_path / "truth.csv"
    output = tmp_path / "output.csv"
    truth.write_text(
        "crm_client_id,loyalty_member_id\nCRM1,LOY1\nCRM2,LOY2\n",
        encoding="utf-8",
    )
    output.write_text(
        "crm_client_id,loyalty_member_id\nCRM1,LOY1\nCRM2,LOY9\n",
        encoding="utf-8",
    )

    quality = loyalty_quality(truth, output)

    assert quality["true_positives"] == 1
    assert quality["false_positives"] == 1
    assert quality["false_negatives"] == 1
