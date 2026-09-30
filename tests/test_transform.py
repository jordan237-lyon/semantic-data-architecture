import pandas as pd

from src.baseline.transform import prepare_finance, prepare_support
from src.baseline.pipeline import add_non_null_match_key


def test_prepare_support_counts_tickets_per_customer():
    source = pd.DataFrame(
        [
            {
                "ticket_id": "TICKET-1",
                "customer_ref": "SUP-1",
                "full_name": "JEAN MARTIN",
                "mail": " JEAN@EXAMPLE.COM ",
                "country_name": "France",
            },
            {
                "ticket_id": "TICKET-2",
                "customer_ref": "SUP-1",
                "full_name": "JEAN MARTIN",
                "mail": " JEAN@EXAMPLE.COM ",
                "country_name": "France",
            },
        ]
    )

    result = prepare_support(source)

    assert len(result) == 1
    assert result.loc[0, "ticket_count"] == 2
    assert result.loc[0, "email_norm"] == "jean@example.com"


def test_prepare_finance_sums_transactions_per_account():
    source = pd.DataFrame(
        [
            {
                "transaction_id": "TX-1",
                "account_id": "ACC-1",
                "customer_name": "Jean Martin",
                "contact_email": "JEAN@EXAMPLE.COM",
                "country_code": "FR",
                "amount": 10.25,
            },
            {
                "transaction_id": "TX-2",
                "account_id": "ACC-1",
                "customer_name": "Jean Martin",
                "contact_email": "JEAN@EXAMPLE.COM",
                "country_code": "FR",
                "amount": 20.50,
            },
        ]
    )

    result = prepare_finance(source)

    assert len(result) == 1
    assert result.loc[0, "revenue"] == 30.75
    assert result.loc[0, "country_norm"] == "France"


def test_baseline_missing_emails_receive_distinct_source_local_keys():
    source = pd.DataFrame({"email_norm": [None, None, "a@example.com"]})

    crm = add_non_null_match_key(source, "crm")
    support = add_non_null_match_key(source, "support")

    assert crm["_match_key"].is_unique
    assert crm.loc[0, "_match_key"] != support.loc[0, "_match_key"]
    assert crm.loc[2, "_match_key"] == support.loc[2, "_match_key"]
