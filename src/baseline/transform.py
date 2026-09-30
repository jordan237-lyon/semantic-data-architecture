
import pandas as pd
import re

COUNTRY_CODE_TO_NAME = {
    "FR": "France",
    "CM": "Cameroon",
    "DE": "Germany",
    "ES": "Spain",
    "BE": "Belgium",
    "CA": "Canada",
    "IT": "Italy",
}

def normalize_email(value):
    if pd.isna(value):
        return None
    value = str(value).strip().lower()
    return value if value else None

def normalize_name(value):
    if pd.isna(value):
        return None
    value = re.sub(r"\s+", " ", str(value).strip())
    return value.title()

def normalize_country(value):
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return COUNTRY_CODE_TO_NAME.get(cleaned.upper(), cleaned.title())

def prepare_crm(df):
    out = df.copy()
    out["canonical_id"] = out["client_id"]
    if "customer_name" in out.columns:
        out["full_name"] = out["customer_name"].apply(normalize_name)
    else:
        out["full_name"] = (
            out["first_name"].fillna("").str.strip() + " " +
            out["last_name"].fillna("").str.strip()
        ).str.strip()
    out["email_norm"] = out["email"].apply(normalize_email)
    out["country_norm"] = out["country"]
    return out[["canonical_id","full_name","email_norm","country_norm","created_at"]]

def prepare_support(df):
    out = df.copy()
    out["canonical_id"] = out["customer_ref"]
    out["full_name"] = out["full_name"].apply(normalize_name)
    out["email_norm"] = out["mail"].apply(normalize_email)
    out["country_norm"] = out["country_name"]
    return (
        out.groupby("canonical_id", as_index=False)
        .agg(
            full_name=("full_name", "first"),
            email_norm=("email_norm", "first"),
            country_norm=("country_norm", "first"),
            ticket_count=("ticket_id", "count"),
        )
    )

def prepare_finance(df):
    out = df.copy()
    out["canonical_id"] = out["account_id"]
    out["full_name"] = out["customer_name"].apply(normalize_name)
    out["email_norm"] = out["contact_email"].apply(normalize_email)
    out["country_norm"] = out["country_code"].apply(normalize_country)
    return (
        out.groupby("canonical_id", as_index=False)
        .agg(
            full_name=("full_name", "first"),
            email_norm=("email_norm", "first"),
            country_norm=("country_norm", "first"),
            revenue=("amount", "sum"),
        )
    )

def prepare_loyalty(df):
    out = df.copy()
    out["canonical_id"] = out["member_id"]
    out["full_name"] = out["display_name"].apply(normalize_name)
    out["email_norm"] = out["email_address"].apply(normalize_email)
    out["country_norm"] = out["market"].apply(normalize_country)
    out["created_at"] = out["joined_on"]
    return out[["canonical_id", "full_name", "email_norm", "country_norm", "created_at"]]
