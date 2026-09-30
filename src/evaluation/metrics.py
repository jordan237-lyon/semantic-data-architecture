
def precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) else 0.0

def recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) else 0.0

def f1_score(p, r):
    return 2 * p * r / (p + r) if (p + r) else 0.0


def evaluate_pairs(predicted, expected):
    """Evaluate two sets of entity-link pairs."""
    predicted = set(predicted)
    expected = set(expected)
    true_positives = predicted & expected
    false_positives = predicted - expected
    false_negatives = expected - predicted

    p = precision(len(true_positives), len(false_positives))
    r = recall(len(true_positives), len(false_negatives))
    return {
        "expected_pairs": len(expected),
        "predicted_pairs": len(predicted),
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives),
        "precision": round(p, 6),
        "recall": round(r, 6),
        "f1_score": round(f1_score(p, r), 6),
    }
