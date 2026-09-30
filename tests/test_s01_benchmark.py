from src.evaluation.s01_benchmark import schema_metrics


def test_s01_schema_metrics_distinguish_review_from_false_acceptance():
    decisions = [
        {"source": "crm", "source_column": "status", "semantic_attribute": "Customer.customer_status", "decision": "review"},
        {"source": "support", "source_column": "status", "semantic_attribute": "Customer.customer_status", "decision": "accepted"},
    ]

    metrics = schema_metrics(decisions)

    assert metrics["candidate_accuracy"] == 0.5
    assert metrics["accepted_incorrect"] == 1
    assert metrics["review_mappings"] == 1
    assert metrics["coverage"] == 0.5
