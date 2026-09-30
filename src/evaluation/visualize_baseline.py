"""Create publication-friendly SVG visuals for the baseline evaluation."""

import csv
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "baseline"
PLOTS = RESULTS / "plots"
EVALUATION = RESULTS / "baseline_evaluation.json"
ERRORS = RESULTS / "baseline_matching_errors.csv"

COLORS = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "orange": "#f59e0b",
    "red": "#dc2626",
    "ink": "#172033",
    "muted": "#667085",
    "grid": "#d8dee9",
    "soft_blue": "#dbeafe",
    "soft_red": "#fee2e2",
    "white": "#ffffff",
}

RELATION_LABELS = {
    "crm_support": "CRM ↔ Support",
    "crm_finance": "CRM ↔ Finance",
    "support_finance": "Support ↔ Finance",
    "overall": "Global",
}


def load_data():
    evaluation = json.loads(EVALUATION.read_text(encoding="utf-8"))
    with ERRORS.open(newline="", encoding="utf-8") as stream:
        errors = list(csv.DictReader(stream))
    return evaluation, errors


def document(width, height, title, description, body):
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["white"]}"/>',
            f'<style>text{{font-family:Arial,sans-serif;fill:{COLORS["ink"]}}}.title{{font-size:25px;font-weight:700}}.subtitle{{font-size:14px;fill:{COLORS["muted"]}}}.heading{{font-size:17px;font-weight:700}}.label{{font-size:13px;font-weight:600}}.small{{font-size:12px;fill:{COLORS["muted"]}}}.value{{font-size:13px;font-weight:700}}.big{{font-size:30px;font-weight:700}}</style>',
            *body,
            "</svg>",
        ]
    )


def score_plot(evaluation, width=1000, height=610):
    body = [
        '<text x="500" y="38" text-anchor="middle" class="title">Qualité du matching par relation</text>',
        '<text x="500" y="63" text-anchor="middle" class="subtitle">Plus le score est proche de 1, meilleure est la correspondance</text>',
    ]
    left, top, chart_width, chart_height = 100, 100, 830, 390
    keys = list(RELATION_LABELS)
    series = [
        ("Précision", "precision", COLORS["blue"]),
        ("Rappel", "recall", COLORS["green"]),
        ("F1", "f1_score", COLORS["orange"]),
    ]
    group_width = chart_width / len(keys)
    bar_width, gap = 40, 8

    for tick in range(6):
        value = tick / 5
        y = top + chart_height - value * chart_height
        body.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="small">{value:.1f}</text>',
            ]
        )

    for group_index, key in enumerate(keys):
        center = left + group_width * (group_index + 0.5)
        start_x = center - (len(series) * bar_width + 2 * gap) / 2
        for series_index, (_, metric, color) in enumerate(series):
            value = evaluation[key][metric]
            bar_height = value * chart_height
            x = start_x + series_index * (bar_width + gap)
            y = top + chart_height - bar_height
            body.extend(
                [
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="{color}"/>',
                    f'<text x="{x + bar_width / 2:.1f}" y="{max(y - 7, 88):.1f}" text-anchor="middle" class="value">{value:.3f}</text>',
                ]
            )
        body.append(
            f'<text x="{center:.1f}" y="520" text-anchor="middle" class="label">{RELATION_LABELS[key]}</text>'
        )

    for index, (name, _, color) in enumerate(series):
        x = 340 + index * 145
        body.extend(
            [
                f'<rect x="{x}" y="560" width="15" height="15" fill="{color}"/>',
                f'<text x="{x + 22}" y="572" class="label">{name}</text>',
            ]
        )
    body.append(
        '<text x="28" y="300" text-anchor="middle" class="small" transform="rotate(-90 28 300)">Score de 0 à 1</text>'
    )
    return document(
        width,
        height,
        "Qualité du matching par relation",
        "Comparaison de la précision, du rappel et du score F1 pour trois relations et le résultat global.",
        body,
    )


def counts_plot(evaluation, width=1000, height=610):
    body = [
        '<text x="500" y="38" text-anchor="middle" class="title">Correspondances correctes et erreurs</text>',
        '<text x="500" y="63" text-anchor="middle" class="subtitle">Nombre de paires d’identifiants par résultat d’évaluation</text>',
    ]
    left, top, chart_width, chart_height = 100, 105, 830, 380
    keys = list(RELATION_LABELS)
    series = [
        ("Vrais positifs", "true_positives", COLORS["green"]),
        ("Faux positifs", "false_positives", COLORS["red"]),
        ("Faux négatifs", "false_negatives", COLORS["orange"]),
    ]
    maximum = max(evaluation[key][metric] for key in keys for _, metric, _ in series)
    axis_max = ((maximum + 49) // 50) * 50
    group_width = chart_width / len(keys)
    bar_width, gap = 40, 8

    for tick in range(6):
        value = round(axis_max * tick / 5)
        y = top + chart_height - value / axis_max * chart_height
        body.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="small">{value}</text>',
            ]
        )

    for group_index, key in enumerate(keys):
        center = left + group_width * (group_index + 0.5)
        start_x = center - (len(series) * bar_width + 2 * gap) / 2
        for series_index, (_, metric, color) in enumerate(series):
            value = evaluation[key][metric]
            bar_height = value / axis_max * chart_height
            x = start_x + series_index * (bar_width + gap)
            y = top + chart_height - bar_height
            body.extend(
                [
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" fill="{color}"/>',
                    f'<text x="{x + bar_width / 2:.1f}" y="{max(y - 7, 92):.1f}" text-anchor="middle" class="value">{value}</text>',
                ]
            )
        body.append(
            f'<text x="{center:.1f}" y="515" text-anchor="middle" class="label">{RELATION_LABELS[key]}</text>'
        )

    for index, (name, _, color) in enumerate(series):
        x = 275 + index * 175
        body.extend(
            [
                f'<rect x="{x}" y="558" width="15" height="15" fill="{color}"/>',
                f'<text x="{x + 22}" y="570" class="label">{name}</text>',
            ]
        )
    body.append(
        '<text x="28" y="300" text-anchor="middle" class="small" transform="rotate(-90 28 300)">Nombre de paires</text>'
    )
    return document(
        width,
        height,
        "Correspondances correctes et erreurs",
        "Volumes de vrais positifs, faux positifs et faux négatifs par relation et au global.",
        body,
    )


def null_matrix_plot(errors, width=850, height=620):
    false_positives = [
        row
        for row in errors
        if row["relation"] == "support_finance"
        and row["error_type"] == "false_positive"
    ]
    left_ids = sorted({row["left_id"] for row in false_positives})
    right_ids = sorted({row["right_id"] for row in false_positives})
    pairs = {(row["left_id"], row["right_id"]) for row in false_positives}
    cell = min(105, 360 / max(len(left_ids), len(right_ids), 1))
    grid_left, grid_top = 300, 155
    body = [
        '<text x="425" y="38" text-anchor="middle" class="title">Pourquoi neuf faux positifs ?</text>',
        '<text x="425" y="66" text-anchor="middle" class="subtitle">Trois clients support sans e-mail ont été associés à trois comptes finance sans e-mail</text>',
        '<text x="520" y="112" text-anchor="middle" class="heading">Comptes finance sans e-mail</text>',
        '<text x="90" y="320" text-anchor="middle" class="heading" transform="rotate(-90 90 320)">Clients support sans e-mail</text>',
    ]

    for column, right_id in enumerate(right_ids):
        x = grid_left + column * cell + cell / 2
        body.append(
            f'<text x="{x:.1f}" y="140" text-anchor="middle" class="label">{escape(right_id)}</text>'
        )
    for row_index, left_id in enumerate(left_ids):
        y = grid_top + row_index * cell
        body.append(
            f'<text x="{grid_left - 18}" y="{y + cell / 2 + 4:.1f}" text-anchor="end" class="label">{escape(left_id)}</text>'
        )
        for column, right_id in enumerate(right_ids):
            x = grid_left + column * cell
            is_error = (left_id, right_id) in pairs
            fill = COLORS["soft_red"] if is_error else COLORS["white"]
            mark = "×" if is_error else ""
            body.extend(
                [
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" fill="{fill}" stroke="{COLORS["grid"]}"/>',
                    f'<text x="{x + cell / 2:.1f}" y="{y + cell / 2 + 11:.1f}" text-anchor="middle" font-size="34" font-weight="700" fill="{COLORS["red"]}">{mark}</text>',
                ]
            )

    body.extend(
        [
            f'<rect x="185" y="515" width="480" height="58" fill="{COLORS["soft_blue"]}"/>',
            '<text x="425" y="539" text-anchor="middle" class="label">Une valeur absente n’est pas une preuve d’identité</text>',
            '<text x="425" y="560" text-anchor="middle" class="subtitle">3 clients × 3 comptes = 9 associations incorrectes</text>',
        ]
    )
    return document(
        width,
        height,
        "Pourquoi neuf faux positifs ?",
        "Matrice trois par trois montrant les neuf associations incorrectes causées par des e-mails absents.",
        body,
    )


def dashboard(evaluation, errors, width=1200, height=850):
    overall = evaluation["overall"]
    relation_keys = ["crm_support", "crm_finance", "support_finance"]
    false_positives = [
        row
        for row in errors
        if row["relation"] == "support_finance"
        and row["error_type"] == "false_positive"
    ]
    left_ids = sorted({row["left_id"] for row in false_positives})
    right_ids = sorted({row["right_id"] for row in false_positives})
    pairs = {(row["left_id"], row["right_id"]) for row in false_positives}
    body = [
        '<text x="600" y="38" text-anchor="middle" class="title">Baseline — lecture visuelle de l’évaluation</text>',
        '<text x="600" y="64" text-anchor="middle" class="subtitle">Matching exact sur l’e-mail normalisé</text>',
        f'<text x="165" y="125" text-anchor="middle" class="big">{overall["f1_score"]:.3f}</text>',
        '<text x="165" y="150" text-anchor="middle" class="small">F1 global</text>',
        f'<text x="420" y="125" text-anchor="middle" class="big">{overall["true_positives"]}</text>',
        '<text x="420" y="150" text-anchor="middle" class="small">associations correctes</text>',
        f'<text x="680" y="125" text-anchor="middle" class="big">{overall["false_positives"]}</text>',
        '<text x="680" y="150" text-anchor="middle" class="small">faux positifs</text>',
        f'<text x="935" y="125" text-anchor="middle" class="big">{overall["false_negatives"]}</text>',
        '<text x="935" y="150" text-anchor="middle" class="small">faux négatifs</text>',
        '<text x="300" y="205" text-anchor="middle" class="heading">F1 par relation</text>',
    ]

    for index, key in enumerate(relation_keys):
        y = 250 + index * 90
        value = evaluation[key]["f1_score"]
        track_x, track_width = 175, 340
        body.extend(
            [
                f'<text x="155" y="{y + 5}" text-anchor="end" class="label">{RELATION_LABELS[key]}</text>',
                f'<line x1="{track_x}" y1="{y}" x2="{track_x + track_width}" y2="{y}" stroke="{COLORS["grid"]}" stroke-width="12"/>',
                f'<line x1="{track_x}" y1="{y}" x2="{track_x + track_width * value:.1f}" y2="{y}" stroke="{COLORS["blue"]}" stroke-width="12"/>',
                f'<circle cx="{track_x + track_width * value:.1f}" cy="{y}" r="9" fill="{COLORS["blue"]}"/>',
                f'<text x="{track_x + track_width + 16}" y="{y + 5}" class="value">{value:.3f}</text>',
            ]
        )

    body.extend(
        [
            '<text x="875" y="205" text-anchor="middle" class="heading">Les neuf faux positifs support-finance</text>',
            '<text x="875" y="228" text-anchor="middle" class="small">Valeurs d’e-mail absentes rapprochées entre elles</text>',
        ]
    )
    cell, grid_left, grid_top = 82, 765, 275
    for column, right_id in enumerate(right_ids):
        x = grid_left + column * cell + cell / 2
        body.append(
            f'<text x="{x:.1f}" y="258" text-anchor="middle" class="small">{escape(right_id)}</text>'
        )
    for row_index, left_id in enumerate(left_ids):
        y = grid_top + row_index * cell
        body.append(
            f'<text x="{grid_left - 14}" y="{y + cell / 2 + 4:.1f}" text-anchor="end" class="small">{escape(left_id)}</text>'
        )
        for column, right_id in enumerate(right_ids):
            x = grid_left + column * cell
            mark = "×" if (left_id, right_id) in pairs else ""
            body.extend(
                [
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{COLORS["soft_red"]}" stroke="{COLORS["grid"]}"/>',
                    f'<text x="{x + cell / 2}" y="{y + cell / 2 + 10}" text-anchor="middle" font-size="30" font-weight="700" fill="{COLORS["red"]}">{mark}</text>',
                ]
            )

    body.extend(
        [
            f'<line x1="80" y1="585" x2="1120" y2="585" stroke="{COLORS["grid"]}"/>',
            '<text x="600" y="630" text-anchor="middle" class="heading">Ce que montre ce premier test</text>',
            f'<rect x="120" y="670" width="20" height="20" fill="{COLORS["green"]}"/>',
            '<text x="155" y="685" class="label">Les relations CRM sont très fiables : aucune mauvaise association.</text>',
            f'<rect x="120" y="718" width="20" height="20" fill="{COLORS["orange"]}"/>',
            '<text x="155" y="733" class="label">La baseline manque 11 associations attendues au total.</text>',
            f'<rect x="120" y="766" width="20" height="20" fill="{COLORS["red"]}"/>',
            '<text x="155" y="781" class="label">L’absence d’e-mail crée un produit croisé de 3 × 3 faux rapprochements.</text>',
            '<text x="600" y="825" text-anchor="middle" class="subtitle">Conclusion : la règle exacte est performante, mais elle confond absence de valeur et égalité.</text>',
        ]
    )
    return document(
        width,
        height,
        "Baseline — lecture visuelle de l’évaluation",
        "Tableau de bord présentant le F1 global, les volumes d’erreurs, les scores par relation et la matrice des faux positifs.",
        body,
    )


def run():
    evaluation, errors = load_data()
    outputs = {
        "baseline_scores_plot.svg": score_plot(evaluation),
        "baseline_matching_counts_plot.svg": counts_plot(evaluation),
        "baseline_null_email_matrix.svg": null_matrix_plot(errors),
        "baseline_evaluation_dashboard.svg": dashboard(evaluation, errors),
    }
    PLOTS.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        path = PLOTS / filename
        path.write_text(content, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    run()
