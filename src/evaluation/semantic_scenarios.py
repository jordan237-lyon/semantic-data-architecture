"""Generate semantic ambiguity scenarios before architecture execution."""

import csv
import json
import shutil
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SOURCE_RAW = ROOT / "data" / "raw"
SOURCE_TRUTH = ROOT / "data" / "ground_truth"
SCENARIOS = ROOT / "data" / "semantic_scenarios"


def _write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_s01(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, destination=None):
    """Create S01: identical column name with two distinct business meanings."""
    source_raw, source_truth = Path(source_raw), Path(source_truth)
    destination = Path(destination) if destination else SCENARIOS / "S01"
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    crm = pd.read_csv(source_raw / "crm.csv")
    support = pd.read_csv(source_raw / "support.csv")
    crm["status"] = ["inactive" if index % 5 == 0 else "active" for index in range(len(crm))]
    support["status"] = ["closed" if index % 20 < 13 else "open" for index in range(len(support))]
    crm.to_csv(raw_dir / "crm.csv", index=False)
    support.to_csv(raw_dir / "support.csv", index=False)
    shutil.copy2(source_raw / "finance.csv", raw_dir / "finance.csv")
    shutil.copy2(source_truth / "entity_mapping.csv", truth_dir / "entity_mapping.csv")

    schema = pd.read_csv(source_truth / "schema_mapping.csv", dtype="string").fillna("")
    additions = pd.DataFrame([
        {"source": "crm", "source_column": "status", "semantic_attribute": "Customer.customer_status", "references": ""},
        {"source": "support", "source_column": "status", "semantic_attribute": "SupportTicket.ticket_status", "references": ""},
    ])
    pd.concat([schema, additions], ignore_index=True).to_csv(
        truth_dir / "schema_mapping.csv", index=False
    )
    _write_csv(
        truth_dir / "incorrect_mappings.csv",
        [
            {
                "source": "crm", "source_column": "status",
                "incorrect_semantic_attribute": "SupportTicket.ticket_status",
                "reason": "Un statut client ne décrit pas le cycle de vie d'un ticket.",
            },
            {
                "source": "support", "source_column": "status",
                "incorrect_semantic_attribute": "Customer.customer_status",
                "reason": "Un statut de ticket ne décrit pas l'état du client.",
            },
        ],
        ["source", "source_column", "incorrect_semantic_attribute", "reason"],
    )
    definitions = {
        "scenario": "S01",
        "attributes": {
            "Customer.customer_status": {
                "definition": "État courant du client dans la relation commerciale.",
                "source": "crm.status",
                "allowed_values": ["active", "inactive"],
                "grain": "customer",
                "expected_a3_decision": "accepted",
            },
            "SupportTicket.ticket_status": {
                "definition": "État de traitement d'un ticket de support.",
                "source": "support.status",
                "allowed_values": ["open", "closed"],
                "grain": "ticket",
                "expected_a3_decision": "accepted",
            },
        },
    }
    (truth_dir / "semantic_definitions.yaml").write_text(
        yaml.safe_dump(definitions, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest = {
        "scenario": "S01",
        "title": "Même nom, sens différent",
        "changed_sources": ["crm", "support"],
        "ambiguous_column": "status",
        "crm_status_distribution": crm["status"].value_counts().sort_index().to_dict(),
        "support_status_distribution": support["status"].value_counts().sort_index().to_dict(),
        "entity_links_modified": False,
        "architectures_executed": [],
    }
    (destination / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def generate_s02(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, destination=None):
    """Create S02: different names for the same transaction-level amount."""
    source_raw, source_truth = Path(source_raw), Path(source_truth)
    destination = Path(destination) if destination else SCENARIOS / "S02"
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source_raw / "crm.csv", raw_dir / "crm.csv")
    shutil.copy2(source_raw / "support.csv", raw_dir / "support.csv")
    finance = pd.read_csv(source_raw / "finance.csv").rename(columns={"amount": "gross_amount"})
    finance.to_csv(raw_dir / "finance.csv", index=False)

    crm = pd.read_csv(source_raw / "crm.csv").iloc[:80].reset_index(drop=True)
    sales_rows = []
    for sale_index in range(120):
        customer_index = sale_index if sale_index < 80 else sale_index - 80
        customer = crm.iloc[customer_index]
        sales_rows.append({
            "sale_id": f"SALE{sale_index + 1:04d}",
            "account_reference": f"SALACC{customer_index + 1:04d}",
            "customer_email": str(customer["email"]).upper() if sale_index % 2 else customer["email"],
            "turnover_value": round(50 + ((sale_index + 1) * 17) % 900 + 0.25, 2),
            "sale_date": f"2025-05-{sale_index % 28 + 1:02d}",
        })
    pd.DataFrame(sales_rows).to_csv(raw_dir / "sales.csv", index=False)

    entities = pd.read_csv(source_truth / "entity_mapping.csv", dtype="string")
    entities["sales_account_reference"] = pd.NA
    entities.loc[:79, "sales_account_reference"] = [f"SALACC{index + 1:04d}" for index in range(80)]
    entities.to_csv(truth_dir / "entity_mapping.csv", index=False)

    schema = pd.read_csv(source_truth / "schema_mapping.csv", dtype="string").fillna("")
    schema.loc[
        (schema["source"] == "finance") & (schema["source_column"] == "amount"),
        "source_column",
    ] = "gross_amount"
    additions = pd.DataFrame([
        {"source": "sales", "source_column": "sale_id", "semantic_attribute": "Transaction.identifier", "references": ""},
        {"source": "sales", "source_column": "account_reference", "semantic_attribute": "Transaction.account_reference", "references": "Customer.identifier"},
        {"source": "sales", "source_column": "customer_email", "semantic_attribute": "Customer.email", "references": ""},
        {"source": "sales", "source_column": "turnover_value", "semantic_attribute": "Transaction.amount", "references": ""},
        {"source": "sales", "source_column": "sale_date", "semantic_attribute": "Transaction.transaction_date", "references": ""},
    ])
    pd.concat([schema, additions], ignore_index=True).to_csv(
        truth_dir / "schema_mapping.csv", index=False
    )
    _write_csv(
        truth_dir / "incorrect_mappings.csv",
        [
            {"source": "finance", "source_column": "gross_amount", "incorrect_semantic_attribute": "Customer.revenue", "reason": "Valeur par transaction, pas revenu déjà agrégé par client."},
            {"source": "sales", "source_column": "turnover_value", "incorrect_semantic_attribute": "Customer.revenue", "reason": "Valeur par vente, pas revenu déjà agrégé par client."},
        ],
        ["source", "source_column", "incorrect_semantic_attribute", "reason"],
    )
    definitions = {
        "scenario": "S02",
        "equivalent_columns": ["finance.gross_amount", "sales.turnover_value"],
        "target": {
            "attribute": "Transaction.amount",
            "definition": "Montant brut porté par une transaction individuelle.",
            "type": "decimal",
            "unit": "currency_unit",
            "grain": "transaction",
        },
        "confusable_target": {
            "attribute": "Customer.revenue",
            "definition": "Somme des montants transactionnels au niveau client.",
            "grain": "customer",
        },
        "expected_a3_decision": "accepted",
    }
    (truth_dir / "semantic_definitions.yaml").write_text(
        yaml.safe_dump(definitions, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest = {
        "scenario": "S02",
        "title": "Noms différents, même sens",
        "finance_change": {"from": "amount", "to": "gross_amount", "rows": len(finance)},
        "new_source": {"name": "sales", "rows": len(sales_rows), "linked_customers": 80},
        "equivalent_columns": ["finance.gross_amount", "sales.turnover_value"],
        "correct_target": "Transaction.amount",
        "confusable_target": "Customer.revenue",
        "architectures_executed": [],
    }
    (destination / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def generate_s03(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, destination=None):
    """Create S03: competing gross and net monthly revenue definitions."""
    source_raw, source_truth = Path(source_raw), Path(source_truth)
    destination = Path(destination) if destination else SCENARIOS / "S03"
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    for source in ("crm", "support", "finance"):
        shutil.copy2(source_raw / f"{source}.csv", raw_dir / f"{source}.csv")

    crm = pd.read_csv(source_raw / "crm.csv").iloc[:100].reset_index(drop=True)
    gross_rows, net_rows = [], []
    for customer_index, customer in crm.iterrows():
        account_id = f"REVACC{customer_index + 1:04d}"
        for month_index, period in enumerate(("2025-05", "2025-06"), start=1):
            gross = round(800 + ((customer_index + 1) * 73 + month_index * 191) % 4200 + 0.75, 2)
            tax_rate = (0.18, 0.20, 0.21)[customer_index % 3]
            refund_rate = (customer_index % 6) / 100
            net = round(gross / (1 + tax_rate) * (1 - refund_rate), 2)
            common = {
                "account_id": account_id,
                "customer_email": customer["email"],
                "period": period,
                "currency": "EUR",
            }
            gross_rows.append({**common, "gross_revenue": gross})
            net_rows.append({**common, "net_revenue": net})
    gross_columns = ["account_id", "customer_email", "period", "gross_revenue", "currency"]
    net_columns = ["account_id", "customer_email", "period", "net_revenue", "currency"]
    pd.DataFrame(gross_rows)[gross_columns].to_csv(raw_dir / "revenue_gross.csv", index=False)
    pd.DataFrame(net_rows)[net_columns].to_csv(raw_dir / "revenue_net.csv", index=False)

    entities = pd.read_csv(source_truth / "entity_mapping.csv", dtype="string")
    entities["gross_revenue_account_id"] = pd.NA
    entities["net_revenue_account_id"] = pd.NA
    account_ids = [f"REVACC{index + 1:04d}" for index in range(100)]
    entities.loc[:99, "gross_revenue_account_id"] = account_ids
    entities.loc[:99, "net_revenue_account_id"] = account_ids
    entities.to_csv(truth_dir / "entity_mapping.csv", index=False)

    schema = pd.read_csv(source_truth / "schema_mapping.csv", dtype="string").fillna("")
    additions = []
    for source, measure in (("revenue_gross", "gross_revenue"), ("revenue_net", "net_revenue")):
        additions.extend([
            {"source": source, "source_column": "account_id", "semantic_attribute": "RevenueSnapshot.account_reference", "references": "Customer.identifier"},
            {"source": source, "source_column": "customer_email", "semantic_attribute": "Customer.email", "references": ""},
            {"source": source, "source_column": "period", "semantic_attribute": "RevenueSnapshot.period", "references": ""},
            {"source": source, "source_column": measure, "semantic_attribute": f"RevenueSnapshot.{measure}", "references": ""},
            {"source": source, "source_column": "currency", "semantic_attribute": "RevenueSnapshot.currency", "references": ""},
        ])
    pd.concat([schema, pd.DataFrame(additions)], ignore_index=True).to_csv(
        truth_dir / "schema_mapping.csv", index=False
    )
    incorrect = [
        {"source": "revenue_gross", "source_column": "gross_revenue", "incorrect_semantic_attribute": "RevenueSnapshot.net_revenue", "reason": "Le brut inclut les taxes et remboursements non déduits."},
        {"source": "revenue_net", "source_column": "net_revenue", "incorrect_semantic_attribute": "RevenueSnapshot.gross_revenue", "reason": "Le net est calculé après taxes et remboursements."},
        {"source": "revenue_gross", "source_column": "gross_revenue", "incorrect_semantic_attribute": "Customer.revenue", "reason": "La mesure est définie au grain client-mois."},
        {"source": "revenue_net", "source_column": "net_revenue", "incorrect_semantic_attribute": "Customer.revenue", "reason": "La mesure est définie au grain client-mois."},
    ]
    _write_csv(
        truth_dir / "incorrect_mappings.csv", incorrect,
        ["source", "source_column", "incorrect_semantic_attribute", "reason"],
    )
    definitions = {
        "scenario": "S03",
        "concept": "RevenueSnapshot",
        "grain": ["customer", "calendar_month"],
        "unit": "EUR",
        "attributes": {
            "gross_revenue": {
                "definition": "Chiffre d'affaires avant déduction des taxes et remboursements.",
                "source": "revenue_gross.gross_revenue",
            },
            "net_revenue": {
                "definition": "Chiffre d'affaires après déduction des taxes et remboursements.",
                "source": "revenue_net.net_revenue",
            },
        },
        "interchangeable": False,
        "expected_a3_decision": "accepted",
    }
    (truth_dir / "semantic_definitions.yaml").write_text(
        yaml.safe_dump(definitions, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    gross_values = pd.Series([row["gross_revenue"] for row in gross_rows])
    net_values = pd.Series([row["net_revenue"] for row in net_rows])
    manifest = {
        "scenario": "S03",
        "title": "Définitions métier concurrentes",
        "sources": {"revenue_gross": len(gross_rows), "revenue_net": len(net_rows)},
        "customers": 100,
        "periods": ["2025-05", "2025-06"],
        "currency": "EUR",
        "gross_net_correlation": round(float(gross_values.corr(net_values)), 6),
        "all_net_values_below_gross": bool((net_values < gross_values).all()),
        "architectures_executed": [],
    }
    (destination / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def generate_s04(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, destination=None):
    """Create S04: unchanged column and type, but a definition change over time."""
    source_raw, source_truth = Path(source_raw), Path(source_truth)
    destination = Path(destination) if destination else SCENARIOS / "S04"
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    crm = pd.read_csv(source_raw / "crm.csv").iloc[:100].reset_index(drop=True)
    rows = []
    for customer_index, customer in crm.iterrows():
        customer_number = customer_index + 1
        recently_active = customer_number % 4 != 0
        paying_contract = customer_number % 5 not in {0, 1}
        common = {
            "customer_id": customer["client_id"],
            "customer_email": customer["email"],
        }
        rows.append({**common, "snapshot_date": "2025-06-30", "active": recently_active})
        rows.append({**common, "snapshot_date": "2025-07-01", "active": paying_contract})

    history = pd.DataFrame(rows)[
        ["customer_id", "customer_email", "snapshot_date", "active"]
    ]
    history.to_csv(raw_dir / "customer_activity.csv", index=False)

    entities = pd.read_csv(source_truth / "entity_mapping.csv", dtype="string")
    entities["customer_activity_customer_id"] = pd.NA
    entities.loc[:99, "customer_activity_customer_id"] = crm["client_id"].tolist()
    entities.to_csv(truth_dir / "entity_mapping.csv", index=False)

    _write_csv(
        truth_dir / "temporal_schema_mapping.csv",
        [
            {
                "source": "customer_activity", "source_column": "active",
                "valid_from": "", "valid_to": "2025-06-30",
                "semantic_attribute": "Customer.recently_active_90d",
                "definition_version": "activity_v1",
            },
            {
                "source": "customer_activity", "source_column": "active",
                "valid_from": "2025-07-01", "valid_to": "",
                "semantic_attribute": "Customer.paying_contract_active",
                "definition_version": "contract_v2",
            },
        ],
        ["source", "source_column", "valid_from", "valid_to", "semantic_attribute", "definition_version"],
    )
    _write_csv(
        truth_dir / "incorrect_mappings.csv",
        [
            {
                "source": "customer_activity", "source_column": "active",
                "incorrect_semantic_attribute": "Customer.active",
                "reason": "Un mapping unique masque la rupture de définition du 2025-07-01.",
            },
            {
                "source": "customer_activity", "source_column": "active",
                "incorrect_semantic_attribute": "Customer.recently_active_90d",
                "reason": "Cette définition n'est valide que jusqu'au 2025-06-30.",
            },
            {
                "source": "customer_activity", "source_column": "active",
                "incorrect_semantic_attribute": "Customer.paying_contract_active",
                "reason": "Cette définition n'est valide qu'à partir du 2025-07-01.",
            },
        ],
        ["source", "source_column", "incorrect_semantic_attribute", "reason"],
    )
    definitions = {
        "scenario": "S04",
        "source": "customer_activity.active",
        "unchanged_properties": {"column_name": "active", "type": "boolean"},
        "break_date": "2025-07-01",
        "versions": {
            "activity_v1": {
                "valid_to": "2025-06-30",
                "attribute": "Customer.recently_active_90d",
                "definition": "Connexion observée au cours des 90 derniers jours.",
            },
            "contract_v2": {
                "valid_from": "2025-07-01",
                "attribute": "Customer.paying_contract_active",
                "definition": "Contrat payant en cours à la date d'observation.",
            },
        },
        "expected_a3_decision": "review",
        "silent_acceptance_allowed": False,
    }
    (truth_dir / "semantic_definitions.yaml").write_text(
        yaml.safe_dump(definitions, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    before = history[history["snapshot_date"] == "2025-06-30"]["active"]
    after = history[history["snapshot_date"] == "2025-07-01"]["active"]
    disagreements = sum(bool(left) != bool(right) for left, right in zip(before, after))
    manifest = {
        "scenario": "S04",
        "title": "Dérive sémantique temporelle",
        "source": "customer_activity",
        "rows": len(history),
        "customers": len(crm),
        "break_date": "2025-07-01",
        "column_name_unchanged": True,
        "column_type_unchanged": True,
        "before_true_rate": round(float(before.mean()), 6),
        "after_true_rate": round(float(after.mean()), 6),
        "customer_level_disagreements": disagreements,
        "expected_decision": "review",
        "architectures_executed": [],
    }
    (destination / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def generate_s05(source_raw=SOURCE_RAW, source_truth=SOURCE_TRUTH, destination=None):
    """Create S05: a customer-like name contradicted by mixed identifier values."""
    source_raw, source_truth = Path(source_raw), Path(source_truth)
    destination = Path(destination) if destination else SCENARIOS / "S05"
    raw_dir, truth_dir = destination / "raw", destination / "ground_truth"
    raw_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)

    crm = pd.read_csv(source_raw / "crm.csv").iloc[:100].reset_index(drop=True)
    mixed_rows = []
    for index, customer in crm.iterrows():
        is_ticket = index < 70
        identifier = f"TKT-{index + 1:05d}" if is_ticket else customer["client_id"]
        mixed_rows.append({
            "event_id": f"EVT-{index + 1:05d}",
            "customer_id": identifier,
            "contact_email": customer["email"],
            "event_type": "support_interaction" if is_ticket else "customer_update",
            "created_at": f"2025-08-{index % 28 + 1:02d}",
        })
    _write_csv(
        raw_dir / "mixed_events.csv",
        mixed_rows,
        ["event_id", "customer_id", "contact_email", "event_type", "created_at"],
    )

    _write_csv(
        truth_dir / "value_ground_truth.csv",
        [
            {
                "row_number": index + 1,
                "value": row["customer_id"],
                "actual_semantic_attribute": (
                    "SupportTicket.identifier" if index < 70 else "Customer.identifier"
                ),
                "value_class": "ticket_id" if index < 70 else "customer_id",
            }
            for index, row in enumerate(mixed_rows)
        ],
        ["row_number", "value", "actual_semantic_attribute", "value_class"],
    )
    _write_csv(
        truth_dir / "schema_mapping.csv",
        [
            {
                "source": "mixed_events", "source_column": "customer_id",
                "semantic_attribute": "AMBIGUOUS_MIXED_IDENTIFIER",
                "expected_decision": "review",
                "reason": "Une colonne unique mélange deux classes d'identifiants.",
            }
        ],
        ["source", "source_column", "semantic_attribute", "expected_decision", "reason"],
    )
    _write_csv(
        truth_dir / "incorrect_mappings.csv",
        [
            {
                "source": "mixed_events", "source_column": "customer_id",
                "incorrect_semantic_attribute": "Customer.identifier",
                "reason": "70 % des valeurs sont des identifiants de tickets.",
            },
            {
                "source": "mixed_events", "source_column": "customer_id",
                "incorrect_semantic_attribute": "SupportTicket.identifier",
                "reason": "30 % des valeurs sont de véritables identifiants clients.",
            },
        ],
        ["source", "source_column", "incorrect_semantic_attribute", "reason"],
    )
    definitions = {
        "scenario": "S05",
        "source": "mixed_events.customer_id",
        "declared_name_suggests": "Customer.identifier",
        "value_patterns": {
            "ticket_id": {"prefix": "TKT-", "share": 0.70, "target": "SupportTicket.identifier"},
            "customer_id": {"prefix": "CRM", "share": 0.30, "target": "Customer.identifier"},
        },
        "single_mapping_valid": False,
        "required_remediation": "Séparer ou typer les valeurs avant le mapping.",
        "expected_a3_decision": "review",
    }
    (truth_dir / "semantic_definitions.yaml").write_text(
        yaml.safe_dump(definitions, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest = {
        "scenario": "S05",
        "title": "Conflit entre nom, type et valeurs",
        "source": "mixed_events",
        "rows": len(mixed_rows),
        "ambiguous_column": "customer_id",
        "string_type_share": 1.0,
        "ticket_identifier_share": 0.70,
        "customer_identifier_share": 0.30,
        "expected_decision": "review",
        "architectures_executed": [],
    }
    (destination / "scenario.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate_s01(), indent=2, ensure_ascii=False))
