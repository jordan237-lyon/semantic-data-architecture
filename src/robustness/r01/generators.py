"""Deterministic, isolated data generators for the R01 pilot."""

import csv
import hashlib
import json
import random
from pathlib import Path

import yaml


SEEDS = (11, 22, 33)
SCENARIOS = ("S01", "S04", "S05")
INTENSITIES = ("I0", "I1", "I2")
S01_OVERLAP = {"I0": 0.0, "I1": 0.5, "I2": 1.0}
S04_DRIFT_POINTS = {"I0": 5, "I1": 15, "I2": 40}
S05_TICKET_SHARE = {"I0": 0.10, "I1": 0.50, "I2": 0.90}


def _write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_yaml(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _customer(index):
    return {
        "customer_id": f"CRM{index + 1:06d}",
        "email": f"client{index + 1:06d}@example.com",
    }


def _noisy_text(value, index, noisy_indexes):
    if index in noisy_indexes:
        return f" {value.upper()} "
    return value


def _missing_indexes(size, rng, noise_rate):
    return set(rng.sample(range(size), round(size * noise_rate)))


def _manifest(scenario, intensity, seed, size, noise_rate, parameters):
    return {
        "campaign": "R01",
        "scenario": scenario,
        "intensity": intensity,
        "seed": seed,
        "size": size,
        "noise_rate": noise_rate,
        "parameters": parameters,
        "architectures_executed": [],
    }


def _generate_s01(destination, intensity, seed, size, noise_rate):
    rng = random.Random(seed)
    crm_missing = _missing_indexes(size, rng, noise_rate)
    support_missing = _missing_indexes(size, rng, noise_rate)
    crm_noisy_emails = _missing_indexes(size, rng, noise_rate)
    support_noisy_emails = _missing_indexes(size, rng, noise_rate)
    crm_rows, support_rows = [], []
    overlap = S01_OVERLAP[intensity]
    support_values = {
        "I0": ("open", "closed"),
        "I1": ("active", "closed"),
        "I2": ("active", "inactive"),
    }[intensity]
    for index in range(size):
        customer = _customer(index)
        crm_rows.append({
            "client_id": customer["customer_id"],
            "email": _noisy_text(customer["email"], index, crm_noisy_emails),
            "status": "active" if rng.random() < 0.8 else "inactive",
            "segment": "" if index in crm_missing else ("business" if index % 3 == 0 else "consumer"),
        })
        support_rows.append({
            "ticket_id": f"TKT-{index + 1:06d}",
            "customer_ref": customer["customer_id"],
            "mail": _noisy_text(customer["email"], index, support_noisy_emails),
            "status": support_values[0] if rng.random() < 0.65 else support_values[1],
            "channel": "" if index in support_missing else ("email" if index % 2 else "web"),
        })
    _write_csv(destination / "raw/crm.csv", crm_rows, ["client_id", "email", "status", "segment"])
    _write_csv(destination / "raw/support.csv", support_rows, ["ticket_id", "customer_ref", "mail", "status", "channel"])
    _write_csv(destination / "ground_truth/schema_mapping.csv", [
        {"source": "crm", "source_column": "status", "semantic_attribute": "Customer.customer_status"},
        {"source": "support", "source_column": "status", "semantic_attribute": "SupportTicket.ticket_status"},
    ], ["source", "source_column", "semantic_attribute"])
    _write_yaml(destination / "ground_truth/semantic_definitions.yaml", {
        "scenario": "R01-S01", "overlap": overlap,
        "attributes": {
            "Customer.customer_status": {"grain": "customer"},
            "SupportTicket.ticket_status": {"grain": "ticket"},
        },
        "expected_a3_decision": "review" if overlap else "accepted",
    })
    return _manifest("S01", intensity, seed, size, noise_rate, {"vocabulary_overlap": overlap})


def _generate_s04(destination, intensity, seed, size, noise_rate):
    rng = random.Random(seed)
    segment_missing = _missing_indexes(size, rng, noise_rate)
    noisy_emails = _missing_indexes(size, rng, noise_rate)
    before_true_count = round(size * 0.70)
    drift_points = S04_DRIFT_POINTS[intensity]
    after_true_count = max(0, before_true_count - round(size * drift_points / 100))
    before_true = set(rng.sample(range(size), before_true_count))
    after_true = set(rng.sample(range(size), after_true_count))
    rows = []
    for index in range(size):
        customer = _customer(index)
        common = {
            "customer_id": customer["customer_id"],
            "customer_email": _noisy_text(customer["email"], index, noisy_emails),
            "segment": "" if index in segment_missing else ("business" if index % 3 == 0 else "consumer"),
        }
        rows.append({**common, "snapshot_date": "2025-06-30", "active": index in before_true})
        rows.append({**common, "snapshot_date": "2025-07-01", "active": index in after_true})
    _write_csv(destination / "raw/customer_activity.csv", rows,
               ["customer_id", "customer_email", "segment", "snapshot_date", "active"])
    _write_csv(destination / "ground_truth/temporal_schema_mapping.csv", [
        {"phase": "before", "semantic_attribute": "Customer.recently_active_90d", "valid_to": "2025-06-30"},
        {"phase": "after", "semantic_attribute": "Customer.paying_contract_active", "valid_to": ""},
    ], ["phase", "semantic_attribute", "valid_to"])
    _write_yaml(destination / "ground_truth/semantic_definitions.yaml", {
        "scenario": "R01-S04", "break_date": "2025-07-01",
        "drift_points": drift_points, "expected_a3_decision": "review",
    })
    return _manifest("S04", intensity, seed, size, noise_rate, {
        "before_true_rate": before_true_count / size,
        "after_true_rate": after_true_count / size,
        "drift_points": drift_points,
    })


def _generate_s05(destination, intensity, seed, size, noise_rate):
    rng = random.Random(seed)
    optional_missing = _missing_indexes(size, rng, noise_rate)
    noisy_emails = _missing_indexes(size, rng, noise_rate)
    ticket_count = round(size * S05_TICKET_SHARE[intensity])
    ticket_indexes = set(rng.sample(range(size), ticket_count))
    rows, truth = [], []
    for index in range(size):
        customer = _customer(index)
        is_ticket = index in ticket_indexes
        identifier = f"TKT-{index + 1:06d}" if is_ticket else customer["customer_id"]
        rows.append({
            "event_id": f"EVT-{index + 1:06d}",
            "customer_id": identifier,
            "contact_email": _noisy_text(customer["email"], index, noisy_emails),
            "event_type": "" if index in optional_missing else ("support_interaction" if is_ticket else "customer_update"),
        })
        truth.append({
            "row_number": index + 1, "value": identifier,
            "actual_semantic_attribute": "SupportTicket.identifier" if is_ticket else "Customer.identifier",
        })
    _write_csv(destination / "raw/mixed_events.csv", rows,
               ["event_id", "customer_id", "contact_email", "event_type"])
    _write_csv(destination / "ground_truth/value_ground_truth.csv", truth,
               ["row_number", "value", "actual_semantic_attribute"])
    _write_yaml(destination / "ground_truth/semantic_definitions.yaml", {
        "scenario": "R01-S05", "ticket_share": ticket_count / size,
        "single_mapping_valid": False, "expected_a3_decision": "review",
    })
    return _manifest("S05", intensity, seed, size, noise_rate, {
        "ticket_share": ticket_count / size,
        "customer_share": (size - ticket_count) / size,
    })


GENERATORS = {"S01": _generate_s01, "S04": _generate_s04, "S05": _generate_s05}


def generate_case(destination, scenario, intensity, seed, size=100, noise_rate=0.05):
    """Generate one isolated R01 dataset and return its manifest."""
    destination = Path(destination)
    scenario, intensity = scenario.upper(), intensity.upper()
    if scenario not in SCENARIOS:
        raise ValueError(f"Scénario R01 inconnu : {scenario}")
    if intensity not in INTENSITIES:
        raise ValueError(f"Intensité R01 inconnue : {intensity}")
    if seed not in SEEDS:
        raise ValueError(f"Graine hors protocole pilote : {seed}")
    if size != 100:
        raise ValueError("Le pilote R01 est gelé à 100 entités.")
    if noise_rate != 0.05:
        raise ValueError("Le pilote R01 est gelé à 5 % de bruit.")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Le dossier R01 doit être vide : {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    manifest = GENERATORS[scenario](destination, intensity, seed, size, noise_rate)
    file_hashes = {}
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            file_hashes[str(path.relative_to(destination))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest["sha256"] = file_hashes
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    return manifest
