"""Audit generated R01 calibration datasets without running A0-A3."""

import csv
import json
from pathlib import Path

import pandas as pd

from src.robustness.r01.generators import INTENSITIES, SCENARIOS
from src.robustness.r01.paths import DATA_ROOT, RESULTS_ROOT


CALIBRATION_SEED = 11
AUDIT_ROOT = RESULTS_ROOT / "calibration"


def _email_noise_rate(series):
    values = series.astype(str)
    return round(float((values != values.str.strip().str.lower()).mean()), 6)


def audit_case(scenario, intensity):
    case = DATA_ROOT / scenario / intensity / f"seed-{CALIBRATION_SEED}"
    manifest = json.loads((case / "manifest.json").read_text(encoding="utf-8"))
    row = {
        "scenario": scenario,
        "intensity": intensity,
        "seed": CALIBRATION_SEED,
        "size": manifest["size"],
        "manifest_files": len(manifest["sha256"]),
        "raw_rows": 0,
        "email_noise_rate": 0.0,
        "optional_missing_rate": 0.0,
        "observed_intensity": 0.0,
        "expected_intensity": 0.0,
        "intensity_matches": False,
    }
    if scenario == "S01":
        crm = pd.read_csv(case / "raw/crm.csv")
        support = pd.read_csv(case / "raw/support.csv")
        overlap = len(set(crm["status"]) & set(support["status"])) / len(set(crm["status"]))
        row.update({
            "raw_rows": len(crm) + len(support),
            "email_noise_rate": round((_email_noise_rate(crm["email"]) + _email_noise_rate(support["mail"])) / 2, 6),
            "optional_missing_rate": round((crm["segment"].isna().mean() + support["channel"].isna().mean()) / 2, 6),
            "observed_intensity": round(overlap, 6),
            "expected_intensity": manifest["parameters"]["vocabulary_overlap"],
        })
    elif scenario == "S04":
        data = pd.read_csv(case / "raw/customer_activity.csv")
        before = data[data["snapshot_date"] == "2025-06-30"]["active"].mean()
        after = data[data["snapshot_date"] == "2025-07-01"]["active"].mean()
        row.update({
            "raw_rows": len(data),
            "email_noise_rate": _email_noise_rate(data.drop_duplicates("customer_id")["customer_email"]),
            "optional_missing_rate": data.drop_duplicates("customer_id")["segment"].isna().mean(),
            "observed_intensity": round((before - after) * 100, 6),
            "expected_intensity": manifest["parameters"]["drift_points"],
        })
    else:
        data = pd.read_csv(case / "raw/mixed_events.csv")
        share = data["customer_id"].astype(str).str.startswith("TKT-").mean()
        row.update({
            "raw_rows": len(data),
            "email_noise_rate": _email_noise_rate(data["contact_email"]),
            "optional_missing_rate": data["event_type"].isna().mean(),
            "observed_intensity": round(float(share), 6),
            "expected_intensity": manifest["parameters"]["ticket_share"],
        })
    row["raw_rows"] = int(row["raw_rows"])
    row["email_noise_rate"] = float(row["email_noise_rate"])
    row["optional_missing_rate"] = float(row["optional_missing_rate"])
    row["observed_intensity"] = float(row["observed_intensity"])
    row["expected_intensity"] = float(row["expected_intensity"])
    row["intensity_matches"] = bool(
        abs(row["observed_intensity"] - row["expected_intensity"]) < 1e-9
    )
    return row


def run():
    rows = [audit_case(scenario, intensity) for scenario in SCENARIOS for intensity in INTENSITIES]
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    with (AUDIT_ROOT / "dataset_audit.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "campaign": "R01",
        "subset": "calibration",
        "datasets_audited": len(rows),
        "all_intensities_match": all(row["intensity_matches"] for row in rows),
        "all_noise_rates_match": all(abs(row["email_noise_rate"] - 0.05) < 1e-9 for row in rows),
        "all_missing_rates_match": all(abs(row["optional_missing_rate"] - 0.05) < 1e-9 for row in rows),
        "rows": rows,
    }
    (AUDIT_ROOT / "dataset_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "rows"}, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    run()
