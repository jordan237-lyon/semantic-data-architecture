"""Technical schema profiler used by A1 without semantic metadata."""

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


def profile_column(series, sample_size=5):
    non_null = series.dropna()
    if pd.api.types.is_integer_dtype(series):
        inferred_type = "integer"
    elif pd.api.types.is_numeric_dtype(series):
        inferred_type = "decimal"
    elif pd.api.types.is_bool_dtype(series):
        inferred_type = "boolean"
    elif not non_null.empty and non_null.map(_is_date).mean() >= 0.9:
        inferred_type = "date"
    else:
        inferred_type = "string"

    values = [str(value).strip() for value in non_null if str(value).strip()]
    detected_format = None
    if values and sum(bool(EMAIL_PATTERN.match(value)) for value in values) / len(values) >= 0.8:
        detected_format = "email"
    elif values and sum(
        len(value) == 2 and value.isalpha() and value.isupper() for value in values
    ) / len(values) >= 0.8:
        detected_format = "country_code"
    elif values and sum(_is_date(value) for value in values) / len(values) >= 0.9:
        detected_format = "date"

    samples = list(dict.fromkeys(str(value) for value in non_null))[:sample_size]
    row_count = len(series)
    return {
        "column": str(series.name),
        "inferred_type": inferred_type,
        "detected_format": detected_format,
        "row_count": row_count,
        "non_null_count": int(non_null.size),
        "null_ratio": round(float(series.isna().mean()), 6) if row_count else 0.0,
        "unique_ratio": round(float(non_null.nunique() / non_null.size), 6) if non_null.size else 0.0,
        "sample_values": samples,
    }


def profile_dataframe(dataframe, source):
    return [{**profile_column(dataframe[column]), "source": source} for column in dataframe]


def profile_csv(path, source=None):
    path = Path(path)
    return profile_dataframe(pd.read_csv(path), source or path.stem)
