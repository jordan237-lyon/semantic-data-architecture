import csv

from src.evaluation.perturbations import generate_p01
from src.evaluation.perturbation_p02 import generate_p02
from src.evaluation.perturbation_p03 import generate_p03
from src.evaluation.scale_experiment import generate_scale_dataset
from src.evaluation.new_source_experiment import generate_loyalty_source


def _rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_p01_renames_only_the_support_email_column(tmp_path):
    source_raw = tmp_path / "source" / "raw"
    source_truth = tmp_path / "source" / "ground_truth"
    scenario = tmp_path / "scenario"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    (source_raw / "crm.csv").write_text("client_id\nCRM1\n", encoding="utf-8")
    (source_raw / "finance.csv").write_text("account_id\nACC1\n", encoding="utf-8")
    (source_raw / "support.csv").write_text(
        "ticket_id,customer_ref,full_name,mail,country_name,created_at\n"
        "T1,SUP1,Jean,jean@example.com,France,2025-01-01\n",
        encoding="utf-8",
    )
    (source_truth / "entity_mapping.csv").write_text(
        "canonical_customer_id,crm_client_id,support_customer_ref,finance_account_id\n"
        "C1,CRM1,SUP1,ACC1\n",
        encoding="utf-8",
    )
    (source_truth / "schema_mapping.csv").write_text(
        "source,source_column,semantic_attribute,references\n"
        "support,mail,Customer.email,\n",
        encoding="utf-8",
    )

    generate_p01(source_raw, source_truth, scenario)

    with (scenario / "raw" / "support.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert "mail" not in rows[0]
    assert rows[0]["customer_email_address"] == "jean@example.com"
    assert (source_raw / "support.csv").read_text(encoding="utf-8").splitlines()[0].endswith(
        ",mail,country_name,created_at"
    )


def test_p02_changes_only_finance_country_values(tmp_path):
    source_raw = tmp_path / "source" / "raw"
    source_truth = tmp_path / "source" / "ground_truth"
    scenario = tmp_path / "scenario"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    (source_raw / "crm.csv").write_text("client_id\nCRM1\n", encoding="utf-8")
    (source_raw / "support.csv").write_text("ticket_id\nT1\n", encoding="utf-8")
    (source_raw / "finance.csv").write_text(
        "account_id,country_code\nACC1,FR\nACC2,IT\n", encoding="utf-8"
    )
    (source_truth / "entity_mapping.csv").write_text("id\nC1\n", encoding="utf-8")
    (source_truth / "schema_mapping.csv").write_text("source,source_column\n", encoding="utf-8")

    manifest = generate_p02(source_raw, source_truth, scenario)

    with (scenario / "raw" / "finance.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["country_code"] for row in rows] == ["france", "italy"]
    assert manifest["change"]["schema_modified"] is False
    assert "FR" in (source_raw / "finance.csv").read_text(encoding="utf-8")


def test_p03_merges_crm_name_columns_without_changing_source(tmp_path):
    source_raw = tmp_path / "source" / "raw"
    source_truth = tmp_path / "source" / "ground_truth"
    scenario = tmp_path / "scenario"
    source_raw.mkdir(parents=True)
    source_truth.mkdir(parents=True)
    (source_raw / "crm.csv").write_text(
        "client_id,first_name,last_name,email,country,created_at\n"
        "CRM1,Jean,Martin,j@example.com,France,2025-01-01\n",
        encoding="utf-8",
    )
    (source_raw / "support.csv").write_text("ticket_id\nT1\n", encoding="utf-8")
    (source_raw / "finance.csv").write_text("transaction_id\nTX1\n", encoding="utf-8")
    (source_truth / "entity_mapping.csv").write_text("id\nC1\n", encoding="utf-8")
    (source_truth / "schema_mapping.csv").write_text(
        "source,source_column,semantic_attribute,references\n"
        "crm,first_name,Customer.full_name,\n"
        "crm,last_name,Customer.full_name,\n",
        encoding="utf-8",
    )

    manifest = generate_p03(source_raw, source_truth, scenario)

    rows = _rows(scenario / "raw" / "crm.csv")
    assert rows[0]["customer_name"] == "Jean Martin"
    assert "first_name" not in rows[0] and "last_name" not in rows[0]
    schema = _rows(scenario / "ground_truth" / "schema_mapping.csv")
    assert schema == [{
        "source": "crm", "source_column": "customer_name",
        "semantic_attribute": "Customer.full_name", "references": "",
    }]
    assert manifest["change"]["column_count_delta"] == -1
    assert "first_name" in (source_raw / "crm.csv").read_text(encoding="utf-8")


def test_scale_dataset_makes_identifiers_and_emails_unique(tmp_path):
    raw = tmp_path / "raw"
    truth = tmp_path / "truth"
    raw.mkdir()
    truth.mkdir()
    (raw / "crm.csv").write_text(
        "client_id,email\nCRM1,a@example.com\n", encoding="utf-8"
    )
    (raw / "support.csv").write_text(
        "ticket_id,customer_ref,mail\nT1,SUP1,a@example.com\n", encoding="utf-8"
    )
    (raw / "finance.csv").write_text(
        "transaction_id,account_id,contact_email\nTX1,ACC1,a@example.com\n",
        encoding="utf-8",
    )
    (truth / "entity_mapping.csv").write_text(
        "canonical_customer_id,crm_client_id,support_customer_ref,finance_account_id\n"
        "C1,CRM1,SUP1,ACC1\n",
        encoding="utf-8",
    )
    (truth / "schema_mapping.csv").write_text("source,source_column\n", encoding="utf-8")

    destination, counts = generate_scale_dataset(2, raw, truth, tmp_path / "scaled")

    crm = _rows(destination / "raw" / "crm.csv")
    support = _rows(destination / "raw" / "support.csv")
    assert counts == {"crm": 2, "support": 2, "finance": 2}
    assert crm[1]["client_id"] == "CRM1-S1"
    assert crm[1]["email"] == "a.scale1@example.com"
    assert support[1]["customer_ref"] == "SUP1-S1"


def test_loyalty_source_is_generated_with_extended_ground_truth(tmp_path):
    raw = tmp_path / "raw"
    truth = tmp_path / "truth"
    destination = tmp_path / "loyalty"
    raw.mkdir()
    truth.mkdir()
    (raw / "crm.csv").write_text(
        "client_id,first_name,last_name,email,country,created_at\n"
        "CRM1,Jean,Martin,j@example.com,France,2025-01-01\n",
        encoding="utf-8",
    )
    (raw / "support.csv").write_text("ticket_id\nT1\n", encoding="utf-8")
    (raw / "finance.csv").write_text("transaction_id\nTX1\n", encoding="utf-8")
    (truth / "entity_mapping.csv").write_text(
        "canonical_customer_id,crm_client_id,support_customer_ref,finance_account_id\n"
        "C1,CRM1,,\n", encoding="utf-8",
    )
    (truth / "schema_mapping.csv").write_text(
        "source,source_column,semantic_attribute,references\n",
        encoding="utf-8",
    )

    manifest = generate_loyalty_source(raw, truth, destination, member_count=1)

    loyalty = _rows(destination / "raw" / "loyalty.csv")
    entity_truth = _rows(destination / "ground_truth" / "entity_mapping.csv")
    assert manifest["rows"] == 1
    assert loyalty[0]["member_id"] == "LOY0001"
    assert loyalty[0]["email_address"] == " J@EXAMPLE.COM "
    assert entity_truth[0]["loyalty_member_id"] == "LOY0001"
