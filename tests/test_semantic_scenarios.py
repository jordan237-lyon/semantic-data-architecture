import csv

from src.evaluation.semantic_scenarios import generate_s01, generate_s02, generate_s03, generate_s04, generate_s05


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_s01_separates_same_named_status_columns(tmp_path):
    source_raw = tmp_path / "source/raw"
    source_truth = tmp_path / "source/ground_truth"
    destination = tmp_path / "S01"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    (source_raw / "crm.csv").write_text(
        "client_id,email\nCRM1,a@example.com\nCRM2,b@example.com\n", encoding="utf-8"
    )
    (source_raw / "support.csv").write_text(
        "ticket_id,customer_ref\nT1,S1\nT2,S2\n", encoding="utf-8"
    )
    (source_raw / "finance.csv").write_text("account_id\nA1\n", encoding="utf-8")
    (source_truth / "entity_mapping.csv").write_text(
        "canonical_customer_id\nC1\n", encoding="utf-8"
    )
    (source_truth / "schema_mapping.csv").write_text(
        "source,source_column,semantic_attribute,references\n", encoding="utf-8"
    )

    manifest = generate_s01(source_raw, source_truth, destination)

    assert set(rows(destination / "raw/crm.csv")[0]) == {"client_id", "email", "status"}
    schema = rows(destination / "ground_truth/schema_mapping.csv")
    assert schema[0]["semantic_attribute"] == "Customer.customer_status"
    assert schema[1]["semantic_attribute"] == "SupportTicket.ticket_status"
    incorrect = rows(destination / "ground_truth/incorrect_mappings.csv")
    assert len(incorrect) == 2
    assert manifest["entity_links_modified"] is False


def test_s02_equates_two_transaction_amount_names_without_using_revenue(tmp_path):
    source_raw = tmp_path / "source/raw"
    source_truth = tmp_path / "source/ground_truth"
    destination = tmp_path / "S02"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    crm_rows = "".join(
        f"CRM{i},client{i}@example.com\n" for i in range(1, 81)
    )
    (source_raw / "crm.csv").write_text("client_id,email\n" + crm_rows, encoding="utf-8")
    (source_raw / "support.csv").write_text("ticket_id\nT1\n", encoding="utf-8")
    (source_raw / "finance.csv").write_text(
        "transaction_id,amount\nTX1,12.50\n", encoding="utf-8"
    )
    entity_rows = "".join(f"C{i},CRM{i}\n" for i in range(1, 81))
    (source_truth / "entity_mapping.csv").write_text(
        "canonical_customer_id,crm_client_id\n" + entity_rows, encoding="utf-8"
    )
    (source_truth / "schema_mapping.csv").write_text(
        "source,source_column,semantic_attribute,references\n"
        "finance,amount,Transaction.amount,\n", encoding="utf-8"
    )

    manifest = generate_s02(source_raw, source_truth, destination)

    assert "gross_amount" in rows(destination / "raw/finance.csv")[0]
    assert len(rows(destination / "raw/sales.csv")) == 120
    truth = rows(destination / "ground_truth/schema_mapping.csv")
    amount_truth = {
        (row["source"], row["source_column"], row["semantic_attribute"])
        for row in truth if row["source_column"] in {"gross_amount", "turnover_value"}
    }
    assert amount_truth == {
        ("finance", "gross_amount", "Transaction.amount"),
        ("sales", "turnover_value", "Transaction.amount"),
    }
    assert manifest["confusable_target"] == "Customer.revenue"


def test_s03_keeps_gross_and_net_revenue_definitions_distinct(tmp_path):
    source_raw = tmp_path / "source/raw"
    source_truth = tmp_path / "source/ground_truth"
    destination = tmp_path / "S03"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    crm_rows = "".join(f"CRM{i},client{i}@example.com\n" for i in range(1, 101))
    (source_raw / "crm.csv").write_text("client_id,email\n" + crm_rows, encoding="utf-8")
    (source_raw / "support.csv").write_text("ticket_id\nT1\n", encoding="utf-8")
    (source_raw / "finance.csv").write_text("transaction_id\nTX1\n", encoding="utf-8")
    entity_rows = "".join(f"C{i},CRM{i}\n" for i in range(1, 101))
    (source_truth / "entity_mapping.csv").write_text(
        "canonical_customer_id,crm_client_id\n" + entity_rows, encoding="utf-8"
    )
    (source_truth / "schema_mapping.csv").write_text(
        "source,source_column,semantic_attribute,references\n", encoding="utf-8"
    )

    manifest = generate_s03(source_raw, source_truth, destination)

    gross = rows(destination / "raw/revenue_gross.csv")
    net = rows(destination / "raw/revenue_net.csv")
    assert len(gross) == len(net) == 200
    assert all(float(net_row["net_revenue"]) < float(gross_row["gross_revenue"]) for gross_row, net_row in zip(gross, net))
    truth = rows(destination / "ground_truth/schema_mapping.csv")
    targets = {row["semantic_attribute"] for row in truth if row["source_column"] in {"gross_revenue", "net_revenue"}}
    assert targets == {"RevenueSnapshot.gross_revenue", "RevenueSnapshot.net_revenue"}
    assert manifest["gross_net_correlation"] > 0.99


def test_s04_records_temporal_definition_break_for_unchanged_active_column(tmp_path):
    source_raw = tmp_path / "source/raw"
    source_truth = tmp_path / "source/ground_truth"
    destination = tmp_path / "S04"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    crm_rows = "".join(f"CRM{i},client{i}@example.com\n" for i in range(1, 101))
    (source_raw / "crm.csv").write_text("client_id,email\n" + crm_rows, encoding="utf-8")
    entity_rows = "".join(f"C{i},CRM{i}\n" for i in range(1, 101))
    (source_truth / "entity_mapping.csv").write_text(
        "canonical_customer_id,crm_client_id\n" + entity_rows, encoding="utf-8"
    )

    manifest = generate_s04(source_raw, source_truth, destination)

    history = rows(destination / "raw/customer_activity.csv")
    assert len(history) == 200
    assert {row["snapshot_date"] for row in history} == {"2025-06-30", "2025-07-01"}
    temporal_truth = rows(destination / "ground_truth/temporal_schema_mapping.csv")
    assert [row["semantic_attribute"] for row in temporal_truth] == [
        "Customer.recently_active_90d", "Customer.paying_contract_active"
    ]
    assert manifest["column_name_unchanged"] is True
    assert manifest["customer_level_disagreements"] > 0
    assert manifest["expected_decision"] == "review"


def test_s05_marks_mixed_customer_id_values_for_review(tmp_path):
    source_raw = tmp_path / "source/raw"
    source_truth = tmp_path / "source/ground_truth"
    destination = tmp_path / "S05"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    crm_rows = "".join(f"CRM{i:04d},client{i}@example.com\n" for i in range(1, 101))
    (source_raw / "crm.csv").write_text("client_id,email\n" + crm_rows, encoding="utf-8")

    manifest = generate_s05(source_raw, source_truth, destination)

    values = rows(destination / "ground_truth/value_ground_truth.csv")
    assert len(values) == 100
    assert sum(row["value_class"] == "ticket_id" for row in values) == 70
    assert sum(row["value_class"] == "customer_id" for row in values) == 30
    schema = rows(destination / "ground_truth/schema_mapping.csv")
    assert schema[0]["semantic_attribute"] == "AMBIGUOUS_MIXED_IDENTIFIER"
    assert schema[0]["expected_decision"] == "review"
    assert manifest["expected_decision"] == "review"
