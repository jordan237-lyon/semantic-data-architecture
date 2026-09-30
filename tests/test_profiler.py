import pandas as pd

from src.semantic.profiler import profile_dataframe


def test_profiler_detects_email_date_decimal_and_nulls():
    dataframe = pd.DataFrame(
        {
            "mail": ["one@example.com", "two@example.com", None],
            "created_at": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "amount": [10.5, 20.25, 30.0],
        }
    )

    profiles = {item["column"]: item for item in profile_dataframe(dataframe, "demo")}

    assert profiles["mail"]["detected_format"] == "email"
    assert profiles["mail"]["null_ratio"] == 0.333333
    assert profiles["created_at"]["inferred_type"] == "date"
    assert profiles["amount"]["inferred_type"] == "decimal"
