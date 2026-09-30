import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _is_date(value):
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return True
    try:
        datetime.fromisoformat(str(value).strip())
        return True
    except (TypeError, ValueError):
        return False


def _infer_type(series):
    non_null = series.dropna()
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_numeric_dtype(series):
        return "decimal"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if not non_null.empty and non_null.map(_is_date).mean() >= 0.9:
        return "date"
    return "string"


def _detect_format(series):
    values = [str(value).strip() for value in series.dropna() if str(value).strip()]
    if not values:
        return None
    email_ratio = sum(bool(EMAIL_PATTERN.match(value)) for value in values) / len(values)
    if email_ratio >= 0.8:
        return "email"
    country_code_ratio = sum(
        len(value) == 2 and value.isalpha() and value.isupper() for value in values
    ) / len(values)
    if country_code_ratio >= 0.8:
        return "country_code"
    if sum(_is_date(value) for value in values) / len(values) >= 0.9:
        return "date"
    return None


def profile_column(series, sample_size=5):
    non_null = series.dropna()
    samples = []
    for value in non_null:
        rendered = str(value)
        if rendered not in samples:
            samples.append(rendered)
        if len(samples) == sample_size:
            break

    row_count = len(series)
    return {
        "column": str(series.name),
        "inferred_type": _infer_type(series),
        "detected_format": _detect_format(series),
        "row_count": row_count,
        "non_null_count": int(non_null.size),
        "null_ratio": round(float(series.isna().mean()), 6) if row_count else 0.0,
        "unique_ratio": round(
            float(non_null.nunique(dropna=True) / non_null.size), 6
        )
        if non_null.size
        else 0.0,
        "sample_values": samples,
    }


def profile_dataframe(dataframe, source):
    profiles = []
    for column in dataframe.columns:
        profile = profile_column(dataframe[column])
        profile["source"] = source
        profiles.append(profile)
    return profiles


def profile_csv(path, source=None):
    path = Path(path)
    return profile_dataframe(pd.read_csv(path), source or path.stem)
