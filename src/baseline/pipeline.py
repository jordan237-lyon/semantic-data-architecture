
from pathlib import Path
import json
import time
import pandas as pd
from src.baseline.transform import prepare_crm, prepare_support, prepare_finance, prepare_loyalty

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "data" / "output"
RESULTS = ROOT / "results" / "baseline"

MANUAL_SCHEMA_MAPPINGS = 19
MANUAL_TRANSFORMATION_RULES = 12


def add_non_null_match_key(dataframe, source):
    """Build a join key where every missing e-mail remains source-local and unique."""
    output = dataframe.rename(columns={"email_norm": f"{source}_email"}).copy()
    email_column = f"{source}_email"
    output["_match_key"] = output[email_column].astype("object")
    missing = output[email_column].isna()
    output.loc[missing, "_match_key"] = [
        f"__missing__:{source}:{index}" for index in output.index[missing]
    ]
    return output

def run(raw_dir=RAW, output_dir=OUTPUT, results_dir=RESULTS):
    start = time.perf_counter()

    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    results_dir = Path(results_dir)
    crm_raw = pd.read_csv(raw_dir / "crm.csv")
    support_raw = pd.read_csv(raw_dir / "support.csv")
    finance_raw = pd.read_csv(raw_dir / "finance.csv")
    loyalty_path = raw_dir / "loyalty.csv"
    loyalty_raw = pd.read_csv(loyalty_path) if loyalty_path.exists() else None

    crm = prepare_crm(crm_raw)
    support = prepare_support(support_raw)
    finance = prepare_finance(finance_raw)
    loyalty = prepare_loyalty(loyalty_raw) if loyalty_raw is not None else None

    # Baseline linkage rule:
    # exact match on normalized email.
    crm_ready = add_non_null_match_key(crm.rename(columns={
        "canonical_id": "crm_client_id",
        "full_name": "crm_full_name",
        "country_norm": "crm_country"
    }), "crm")
    support_ready = add_non_null_match_key(support.rename(columns={
        "canonical_id": "support_customer_ref",
        "full_name": "support_full_name",
        "country_norm": "support_country"
    }), "support")
    finance_ready = add_non_null_match_key(finance.rename(columns={
        "canonical_id": "finance_account_id",
        "full_name": "finance_full_name",
        "country_norm": "finance_country"
    }), "finance")

    unified = crm_ready.merge(support_ready, on="_match_key", how="outer")
    unified = unified.merge(finance_ready, on="_match_key", how="outer")

    email_columns = ["crm_email", "support_email", "finance_email"]
    if loyalty is not None:
        loyalty_ready = add_non_null_match_key(loyalty.rename(columns={
            "canonical_id": "loyalty_member_id",
            "full_name": "loyalty_full_name",
            "country_norm": "loyalty_country",
            "created_at": "loyalty_created_at",
        }), "loyalty")
        unified = unified.merge(loyalty_ready, on="_match_key", how="outer")
        email_columns.append("loyalty_email")

    unified["email_norm"] = unified["crm_email"]
    for email_column in email_columns[1:]:
        unified["email_norm"] = unified["email_norm"].combine_first(
            unified[email_column]
        )
    unified = unified.drop(
        columns=["_match_key", *email_columns]
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / "unified_customer_baseline.csv"
    unified.to_csv(out_path, index=False)

    elapsed = time.perf_counter() - start
    metrics = {
        "pipeline": "baseline_manual_etl",
        "execution_time_seconds": round(elapsed, 6),
        "manual_schema_mappings": MANUAL_SCHEMA_MAPPINGS + (5 if loyalty is not None else 0),
        "manual_transformation_rules": MANUAL_TRANSFORMATION_RULES + (5 if loyalty is not None else 0),
        "crm_raw_rows": int(len(crm_raw)),
        "support_raw_tickets": int(len(support_raw)),
        "support_customers_after_aggregation": int(len(support)),
        "finance_raw_transactions": int(len(finance_raw)),
        "finance_accounts_after_aggregation": int(len(finance)),
        "loyalty_rows": int(len(loyalty_raw)) if loyalty_raw is not None else 0,
        "output_rows": int(len(unified)),
        "output_columns": int(len(unified.columns)),
        "matched_support_rows_by_email": int(unified["support_customer_ref"].notna().sum()),
        "matched_finance_rows_by_email": int(unified["finance_account_id"].notna().sum()),
    }
    (results_dir / "baseline_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))
    print(f"\nOutput: {out_path}")

if __name__ == "__main__":
    run()
