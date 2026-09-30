import pandas as pd

from src.robustness.r01.run_calibration_case import evaluate_predictions, target_from_prefix


def test_r01_prefix_rules_separate_ticket_and_customer_identifiers():
    rules = [
        {"prefix": "TKT-", "target": "SupportTicket.identifier"},
        {"prefix": "CRM", "target": "Customer.identifier"},
    ]
    assert target_from_prefix("TKT-000001", rules) == "SupportTicket.identifier"
    assert target_from_prefix("CRM000001", rules) == "Customer.identifier"
    assert target_from_prefix("UNKNOWN", rules) is None


def test_r01_value_evaluation_counts_silent_errors():
    truth = pd.DataFrame([
        {"row_number": 1, "value": "TKT-1", "actual_semantic_attribute": "SupportTicket.identifier"},
        {"row_number": 2, "value": "CRM1", "actual_semantic_attribute": "Customer.identifier"},
    ])
    predictions = pd.DataFrame([
        {"row_number": 1, "value": "TKT-1", "predicted_semantic_attribute": "Customer.identifier"},
        {"row_number": 2, "value": "CRM1", "predicted_semantic_attribute": "Customer.identifier"},
    ])
    result = evaluate_predictions(predictions, truth)
    assert result["correct_rows"] == 1
    assert result["incorrect_rows"] == 1
    assert result["f1_score"] == 0.5
