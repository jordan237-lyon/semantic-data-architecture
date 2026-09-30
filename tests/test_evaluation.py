from src.evaluation.metrics import evaluate_pairs


def test_evaluate_pairs_counts_matches_and_errors():
    expected = {("CRM1", "SUP1"), ("CRM2", "SUP2")}
    predicted = {("CRM1", "SUP1"), ("CRM3", "SUP3")}

    result = evaluate_pairs(predicted, expected)

    assert result["true_positives"] == 1
    assert result["false_positives"] == 1
    assert result["false_negatives"] == 1
    assert result["precision"] == 0.5
    assert result["recall"] == 0.5
    assert result["f1_score"] == 0.5


def test_evaluate_pairs_deduplicates_links():
    expected = [("CRM1", "SUP1")]
    predicted = [("CRM1", "SUP1"), ("CRM1", "SUP1")]

    result = evaluate_pairs(predicted, expected)

    assert result["predicted_pairs"] == 1
    assert result["true_positives"] == 1
