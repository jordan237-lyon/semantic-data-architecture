import csv
import json
import time
from html import escape
from pathlib import Path

from src.evaluation.metrics import evaluate_pairs


ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH = ROOT / "data" / "ground_truth" / "entity_mapping.csv"
BASELINE_OUTPUT = ROOT / "data" / "output" / "unified_customer_baseline.csv"
RESULTS = ROOT / "results" / "baseline"

RELATIONS = {
    "crm_support": ("crm_client_id", "support_customer_ref"),
    "crm_finance": ("crm_client_id", "finance_account_id"),
    "support_finance": ("support_customer_ref", "finance_account_id"),
}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def extract_pairs(rows, left_column, right_column):
    return {
        (row[left_column], row[right_column])
        for row in rows
        if row.get(left_column) and row.get(right_column)
    }


def write_errors(path, errors):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["relation", "error_type", "left_id", "right_id"],
        )
        writer.writeheader()
        writer.writerows(errors)


def write_plot(path, evaluations):
    labels = ["CRM ↔ Support", "CRM ↔ Finance", "Support ↔ Finance", "Global"]
    keys = ["crm_support", "crm_finance", "support_finance", "overall"]
    series = [
        ("Précision", "precision", "#2563eb"),
        ("Rappel", "recall", "#16a34a"),
        ("F1", "f1_score", "#f59e0b"),
    ]
    width, height = 1000, 600
    left, top, chart_width, chart_height = 90, 80, 850, 400
    group_width = chart_width / len(keys)
    bar_width = 42
    gap = 8

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.title{font-size:24px;font-weight:700}.axis{font-size:13px}.label{font-size:13px;font-weight:600}.value{font-size:12px;font-weight:700}</style>',
        '<text x="500" y="38" text-anchor="middle" class="title">Évaluation du matching de la baseline</text>',
    ]

    for tick in range(6):
        value = tick / 5
        y = top + chart_height - value * chart_height
        svg.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="#d8dee9" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="axis">{value:.1f}</text>'
        )

    for group_index, (key, label) in enumerate(zip(keys, labels)):
        center = left + group_width * (group_index + 0.5)
        total_bar_width = len(series) * bar_width + (len(series) - 1) * gap
        start_x = center - total_bar_width / 2
        for series_index, (_, metric, color) in enumerate(series):
            value = evaluations[key][metric]
            bar_height = value * chart_height
            x = start_x + series_index * (bar_width + gap)
            y = top + chart_height - bar_height
            svg.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="{color}"/>'
            )
            svg.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{max(y - 7, 68):.1f}" text-anchor="middle" class="value">{value:.3f}</text>'
            )
        svg.append(
            f'<text x="{center:.1f}" y="510" text-anchor="middle" class="label">{escape(label)}</text>'
        )

    legend_x = 330
    for index, (name, _, color) in enumerate(series):
        x = legend_x + index * 150
        svg.append(f'<rect x="{x}" y="550" width="16" height="16" fill="{color}"/>')
        svg.append(f'<text x="{x + 24}" y="563" class="axis">{name}</text>')

    svg.append(
        '<text x="24" y="280" text-anchor="middle" class="axis" transform="rotate(-90 24 280)">Score (0 à 1)</text>'
    )
    svg.append("</svg>")
    path.write_text("\n".join(svg), encoding="utf-8")


def evaluate_entity_rows(truth_rows, predicted_rows):
    evaluations = {}
    errors = []
    expected_overall = set()
    predicted_overall = set()

    for relation, (left_column, right_column) in RELATIONS.items():
        expected = extract_pairs(truth_rows, left_column, right_column)
        predicted = extract_pairs(predicted_rows, left_column, right_column)
        evaluations[relation] = evaluate_pairs(predicted, expected)

        expected_overall.update((relation, *pair) for pair in expected)
        predicted_overall.update((relation, *pair) for pair in predicted)
        errors.extend(
            {
                "relation": relation,
                "error_type": "false_positive",
                "left_id": left_id,
                "right_id": right_id,
            }
            for left_id, right_id in sorted(predicted - expected)
        )
        errors.extend(
            {
                "relation": relation,
                "error_type": "false_negative",
                "left_id": left_id,
                "right_id": right_id,
            }
            for left_id, right_id in sorted(expected - predicted)
        )
    evaluations["overall"] = evaluate_pairs(predicted_overall, expected_overall)
    return evaluations, errors


def run():
    started_at = time.perf_counter()
    truth_rows = read_csv(GROUND_TRUTH)
    predicted_rows = read_csv(BASELINE_OUTPUT)
    evaluations, errors = evaluate_entity_rows(truth_rows, predicted_rows)
    evaluations["evaluation_time_seconds"] = round(
        time.perf_counter() - started_at, 6
    )

    RESULTS.mkdir(parents=True, exist_ok=True)
    evaluation_path = RESULTS / "baseline_evaluation.json"
    errors_path = RESULTS / "baseline_matching_errors.csv"
    plot_path = RESULTS / "baseline_evaluation_plot.svg"
    evaluation_path.write_text(
        json.dumps(evaluations, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_errors(errors_path, errors)
    write_plot(plot_path, evaluations)

    print(json.dumps(evaluations, indent=2, ensure_ascii=False))
    print(f"\nErrors: {errors_path}")
    print(f"Plot: {plot_path}")


if __name__ == "__main__":
    run()
