"""Generate SVG explanations of semantic schema-matching results."""

import csv
import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_RESULTS = ROOT / "results" / "semantic"
PLOTS = SEMANTIC_RESULTS / "plots"

COLORS = {
    "accepted": "#16a34a",
    "review": "#f59e0b",
    "rejected": "#dc2626",
    "blue": "#2563eb",
    "purple": "#7c3aed",
    "ink": "#172033",
    "muted": "#667085",
    "grid": "#d8dee9",
    "soft": "#f4f6f8",
    "soft_blue": "#dbeafe",
    "soft_orange": "#fef3c7",
    "white": "#ffffff",
}


def load_results():
    metrics = json.loads(
        (SEMANTIC_RESULTS / "schema_confidence_metrics.json").read_text(
            encoding="utf-8"
        )
    )
    with (SEMANTIC_RESULTS / "semantic_schema_decisions.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        decisions = list(csv.DictReader(stream))
    for row in decisions:
        for field in (
            "name_score",
            "type_score",
            "value_score",
            "total_score",
            "second_score",
            "score_margin",
        ):
            row[field] = float(row[field])
    return metrics, decisions


def svg_document(width, height, title, description, body):
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


def semantic_dashboard(metrics, decisions, width=1100, height=720):
    counts = {
        "accepted": metrics["accepted_mappings"],
        "review": metrics["mappings_requiring_review"],
        "rejected": metrics["rejected_mappings"],
    }
    total = metrics["total_columns"]
    by_source = defaultdict(Counter)
    for row in decisions:
        by_source[row["source"]][row["decision"]] += 1
    reviews = [row for row in decisions if row["decision"] == "review"]
    body = [
        '<text x="550" y="38" text-anchor="middle" class="title">Matching sémantique — synthèse des décisions</text>',
        '<text x="550" y="64" text-anchor="middle" class="subtitle">Politique fondée sur le score du meilleur candidat et sa marge</text>',
        f'<text x="165" y="128" text-anchor="middle" class="big">{total}</text>',
        '<text x="165" y="151" text-anchor="middle" class="small">colonnes analysées</text>',
        f'<text x="425" y="128" text-anchor="middle" class="big">{counts["accepted"]}</text>',
        '<text x="425" y="151" text-anchor="middle" class="small">acceptées automatiquement</text>',
        f'<text x="685" y="128" text-anchor="middle" class="big">{counts["review"]}</text>',
        '<text x="685" y="151" text-anchor="middle" class="small">validations humaines</text>',
        f'<text x="945" y="128" text-anchor="middle" class="big">{metrics["automation_rate"] * 100:.2f} %</text>',
        '<text x="945" y="151" text-anchor="middle" class="small">taux d’automatisation</text>',
        '<text x="550" y="208" text-anchor="middle" class="heading">Répartition globale</text>',
    ]
    bar_x, bar_y, bar_width, bar_height = 100, 232, 900, 38
    cursor = bar_x
    for decision in ("accepted", "review", "rejected"):
        segment = bar_width * counts[decision] / total if total else 0
        if segment:
            body.append(
                f'<rect x="{cursor:.1f}" y="{bar_y}" width="{segment:.1f}" height="{bar_height}" fill="{COLORS[decision]}"/>'
            )
            if segment > 55:
                body.append(
                    f'<text x="{cursor + segment / 2:.1f}" y="257" text-anchor="middle" font-size="13" font-weight="700" fill="white">{counts[decision]}</text>'
                )
        cursor += segment
    legend = (("accepted", "Accepté"), ("review", "À valider"), ("rejected", "Rejeté"))
    for index, (decision, label) in enumerate(legend):
        x = 350 + index * 155
        body.extend(
            [
                f'<rect x="{x}" y="288" width="15" height="15" fill="{COLORS[decision]}"/>',
                f'<text x="{x + 22}" y="300" class="label">{label}</text>',
            ]
        )

    body.append('<text x="315" y="355" text-anchor="middle" class="heading">Décisions par source</text>')
    for row_index, source in enumerate(("crm", "support", "finance")):
        y = 395 + row_index * 62
        body.append(f'<text x="130" y="{y + 5}" class="label">{source.upper()}</text>')
        cursor = 220
        source_total = sum(by_source[source].values())
        for decision in ("accepted", "review", "rejected"):
            segment = 360 * by_source[source][decision] / source_total if source_total else 0
            if segment:
                body.append(
                    f'<rect x="{cursor:.1f}" y="{y - 17}" width="{segment:.1f}" height="30" fill="{COLORS[decision]}"/>'
                )
                body.append(
                    f'<text x="{cursor + segment / 2:.1f}" y="{y + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="white">{by_source[source][decision]}</text>'
                )
            cursor += segment

    body.extend(
        [
            '<text x="825" y="355" text-anchor="middle" class="heading">Cas nécessitant une validation</text>',
            f'<rect x="640" y="380" width="370" height="180" fill="{COLORS["soft_orange"]}"/>',
        ]
    )
    for index, row in enumerate(reviews):
        y = 420 + index * 65
        body.extend(
            [
                f'<text x="665" y="{y}" class="label">{escape(row["source"])}.{escape(row["source_column"])}</text>',
                f'<text x="665" y="{y + 22}" class="small">→ {escape(row["semantic_attribute"])} · score {row["total_score"]:.3f} · marge {row["score_margin"]:.3f}</text>',
            ]
        )
    body.extend(
        [
            f'<line x1="80" y1="605" x2="1020" y2="605" stroke="{COLORS["grid"]}"/>',
            '<text x="550" y="647" text-anchor="middle" class="heading">Lecture principale</text>',
            '<text x="550" y="677" text-anchor="middle" class="label">Le moteur automatise 17 décisions, mais isole les deux dates ambiguës au lieu de décider silencieusement.</text>',
        ]
    )
    return svg_document(
        width,
        height,
        "Matching sémantique — synthèse des décisions",
        "Tableau de bord montrant dix-neuf colonnes, dix-sept acceptations et deux validations humaines.",
        body,
    )


def confidence_scatter(metrics, decisions, width=1100, height=720):
    thresholds = metrics["matching_policy"]["thresholds"]
    scores = [row["total_score"] for row in decisions]
    margins = [row["score_margin"] for row in decisions]
    x_min = max(0.0, min(min(scores), thresholds["review_score"]) - 0.05)
    x_max = min(1.02, max(scores) + 0.02)
    y_min = 0.0
    y_max = min(1.0, max(max(margins), thresholds["auto_accept_margin"]) + 0.05)
    left, top, chart_width, chart_height = 105, 100, 900, 500

    def x_scale(value):
        return left + (value - x_min) / (x_max - x_min) * chart_width

    def y_scale(value):
        return top + chart_height - (value - y_min) / (y_max - y_min) * chart_height

    body = [
        '<text x="550" y="38" text-anchor="middle" class="title">Score élevé ne signifie pas toujours décision certaine</text>',
        '<text x="550" y="64" text-anchor="middle" class="subtitle">Chaque point représente une colonne source</text>',
        f'<rect x="{left}" y="{top}" width="{chart_width}" height="{chart_height}" fill="none" stroke="{COLORS["grid"]}"/>',
    ]
    for tick in range(6):
        x_value = x_min + (x_max - x_min) * tick / 5
        x = x_scale(x_value)
        body.extend(
            [
                f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_height}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{x:.1f}" y="625" text-anchor="middle" class="small">{x_value:.2f}</text>',
            ]
        )
        y_value = y_min + (y_max - y_min) * tick / 5
        y = y_scale(y_value)
        body.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="small">{y_value:.2f}</text>',
            ]
        )
    accept_x = x_scale(thresholds["auto_accept_score"])
    margin_y = y_scale(thresholds["auto_accept_margin"])
    body.extend(
        [
            f'<line x1="{accept_x:.1f}" y1="{top}" x2="{accept_x:.1f}" y2="{top + chart_height}" stroke="{COLORS["purple"]}" stroke-width="2" stroke-dasharray="7 6"/>',
            f'<text x="{accept_x + 8:.1f}" y="{top + 18}" class="small">score 0,85</text>',
            f'<line x1="{left}" y1="{margin_y:.1f}" x2="{left + chart_width}" y2="{margin_y:.1f}" stroke="{COLORS["purple"]}" stroke-width="2" stroke-dasharray="7 6"/>',
            f'<text x="{left + 8}" y="{margin_y - 8:.1f}" class="small">marge 0,10</text>',
        ]
    )
    offsets = Counter()
    for row in decisions:
        key = (round(row["total_score"], 3), round(row["score_margin"], 3))
        offset = offsets[key]
        offsets[key] += 1
        x = x_scale(row["total_score"]) - min(offset, 3) * 5
        y = y_scale(row["score_margin"]) - (offset // 4) * 7
        body.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{COLORS[row["decision"]]}" stroke="white" stroke-width="1.5"/>'
        )
        if row["decision"] != "accepted":
            anchor = "end" if x > left + chart_width * 0.75 else "start"
            label_x = x - 12 if anchor == "end" else x + 12
            body.append(
                f'<text x="{label_x:.1f}" y="{y - 9:.1f}" text-anchor="{anchor}" class="label">{escape(row["source"])}.{escape(row["source_column"])}</text>'
            )
    body.extend(
        [
            '<text x="555" y="675" text-anchor="middle" class="label">Score total du meilleur candidat</text>',
            '<text x="27" y="350" text-anchor="middle" class="label" transform="rotate(-90 27 350)">Marge avec le second candidat</text>',
        ]
    )
    for index, (decision, label) in enumerate(
        (("accepted", "Accepté"), ("review", "À valider"), ("rejected", "Rejeté"))
    ):
        x = 700 + index * 105
        body.extend(
            [
                f'<circle cx="{x}" cy="78" r="6" fill="{COLORS[decision]}"/>',
                f'<text x="{x + 12}" y="82" class="small">{label}</text>',
            ]
        )
    return svg_document(
        width,
        height,
        "Score et marge des correspondances sémantiques",
        "Nuage de points montrant les seuils d'acceptation et les deux colonnes de date envoyées en validation.",
        body,
    )


def _heat_color(value):
    palette = ["#eff6ff", "#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa", "#2563eb"]
    return palette[min(int(max(0.0, min(value, 1.0)) * len(palette)), len(palette) - 1)]


def score_components(decisions, width=1150, height=1080):
    fields = [
        ("name_score", "Nom"),
        ("type_score", "Type"),
        ("value_score", "Valeurs"),
        ("total_score", "Total"),
        ("score_margin", "Marge"),
    ]
    label_x, grid_x, top, cell_width, row_height = 270, 300, 118, 125, 45
    body = [
        '<text x="575" y="38" text-anchor="middle" class="title">Décomposition des scores par colonne</text>',
        '<text x="575" y="64" text-anchor="middle" class="subtitle">La marge révèle l’ambiguïté que le score total ne montre pas</text>',
    ]
    for column, (_, label) in enumerate(fields):
        body.append(
            f'<text x="{grid_x + column * cell_width + cell_width / 2}" y="98" text-anchor="middle" class="label">{label}</text>'
        )
    for row_index, row in enumerate(decisions):
        y = top + row_index * row_height
        label = f'{row["source"]}.{row["source_column"]}'
        body.append(
            f'<text x="{label_x}" y="{y + 28}" text-anchor="end" class="label">{escape(label)}</text>'
        )
        for column, (field, _) in enumerate(fields):
            value = row[field]
            x = grid_x + column * cell_width
            body.extend(
                [
                    f'<rect x="{x}" y="{y}" width="{cell_width - 5}" height="{row_height - 5}" fill="{_heat_color(value)}"/>',
                    f'<text x="{x + (cell_width - 5) / 2}" y="{y + 26}" text-anchor="middle" class="value">{value:.3f}</text>',
                ]
            )
        decision_x = grid_x + len(fields) * cell_width + 28
        body.extend(
            [
                f'<circle cx="{decision_x}" cy="{y + 20}" r="7" fill="{COLORS[row["decision"]]}"/>',
                f'<text x="{decision_x + 14}" y="{y + 25}" class="small">{row["decision"]}</text>',
            ]
        )
    body.extend(
        [
            f'<rect x="{grid_x}" y="{top + len(decisions) * row_height + 25}" width="180" height="15" fill="url(#heatGradient)"/>',
            f'<defs><linearGradient id="heatGradient"><stop offset="0%" stop-color="#eff6ff"/><stop offset="100%" stop-color="{COLORS["blue"]}"/></linearGradient></defs>',
            f'<text x="{grid_x}" y="{top + len(decisions) * row_height + 60}" class="small">0 — faible</text>',
            f'<text x="{grid_x + 180}" y="{top + len(decisions) * row_height + 60}" text-anchor="end" class="small">1 — élevé</text>',
        ]
    )
    return svg_document(
        width,
        height,
        "Décomposition des scores par colonne",
        "Matrice de dix-neuf colonnes montrant les scores de nom, type, valeurs, total et marge.",
        body,
    )


def semantic_flow(width=1250, height=360):
    steps = [
        ("Sources", "CRM · Support · Finance"),
        ("Profilage", "types · formats · nulls"),
        ("Modèle YAML", "concepts · synonymes"),
        ("Scoring", "50 % · 20 % · 30 %"),
        ("Classement", "meilleur · second · marge"),
        ("Décision", "accepté · revue · rejeté"),
    ]
    body = [
        '<text x="625" y="38" text-anchor="middle" class="title">Parcours du matching sémantique</text>',
        '<text x="625" y="64" text-anchor="middle" class="subtitle">De la colonne brute à une décision explicable</text>',
    ]
    start_x, y, box_width, box_height, gap = 35, 125, 165, 92, 38
    for index, (title, detail) in enumerate(steps):
        x = start_x + index * (box_width + gap)
        body.extend(
            [
                f'<rect x="{x}" y="{y}" width="{box_width}" height="{box_height}" rx="5" fill="{COLORS["soft_blue"]}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{x + box_width / 2}" y="{y + 37}" text-anchor="middle" class="heading">{title}</text>',
                f'<text x="{x + box_width / 2}" y="{y + 64}" text-anchor="middle" class="small">{detail}</text>',
            ]
        )
        if index < len(steps) - 1:
            line_start = x + box_width + 7
            line_end = x + box_width + gap - 7
            body.extend(
                [
                    f'<line x1="{line_start}" y1="{y + box_height / 2}" x2="{line_end}" y2="{y + box_height / 2}" stroke="{COLORS["blue"]}" stroke-width="2"/>',
                    f'<path d="M {line_end - 7} {y + box_height / 2 - 5} L {line_end} {y + box_height / 2} L {line_end - 7} {y + box_height / 2 + 5}" fill="none" stroke="{COLORS["blue"]}" stroke-width="2"/>',
                ]
            )
    body.extend(
        [
            '<text x="625" y="280" text-anchor="middle" class="label">Sorties auditables : profil, candidats, composantes du score, marge et justification de la décision</text>',
            '<text x="625" y="312" text-anchor="middle" class="subtitle">Les seuils restent configurables dans semantic/model.yaml</text>',
        ]
    )
    return svg_document(
        width,
        height,
        "Parcours du matching sémantique",
        "Flux en six étapes allant des trois sources aux décisions acceptées, revues ou rejetées.",
        body,
    )


def run():
    metrics, decisions = load_results()
    outputs = {
        "semantic_dashboard.svg": semantic_dashboard(metrics, decisions),
        "confidence_scatter.svg": confidence_scatter(metrics, decisions),
        "score_components.svg": score_components(decisions),
        "semantic_matching_flow.svg": semantic_flow(),
    }
    PLOTS.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        path = PLOTS / filename
        path.write_text(content, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    run()
