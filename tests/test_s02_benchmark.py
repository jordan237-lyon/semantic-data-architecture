from src.evaluation.s02_benchmark import mapping_metrics


def test_s02_counts_revenue_confusion_as_false_acceptance():
    decisions = [
        {"source": "finance", "source_column": "gross_amount", "semantic_attribute": "Transaction.amount", "decision": "accepted"},
        {"source": "sales", "source_column": "turnover_value", "semantic_attribute": "Customer.revenue", "decision": "accepted"},
    ]

    metrics = mapping_metrics(decisions)

    assert metrics["accepted_correct"] == 1
    assert metrics["accepted_incorrect"] == 1
    assert metrics["accepted_as_customer_revenue"] == 1
    assert metrics["f1_score"] == 0.5
