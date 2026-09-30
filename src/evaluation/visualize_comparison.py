"""Generate SVG plots comparing the manual and semantic pipelines."""

import csv
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPARISON = ROOT / "results" / "comparison"
PLOTS = COMPARISON / "plots"

COLORS = {
    "baseline": "#64748b",
    "semantic": "#2563eb",
    "good": "#16a34a",
    "warning": "#f59e0b",
    "bad": "#dc2626",
    "ink": "#172033",
    "muted": "#667085",
    "grid": "#d8dee9",
    "soft_blue": "#dbeafe",
    "soft": "#f4f6f8",
    "white": "#ffffff",
}


def load_results():
    benchmark = json.loads(
        (COMPARISON / "benchmark_summary.json").read_text(encoding="utf-8")
    )
    effort = json.loads(
        (COMPARISON / "effort_comparison.json").read_text(encoding="utf-8")
    )
    with (COMPARISON / "quality_comparison.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        quality = {row["metric"]: row for row in csv.DictReader(stream)}
    for row in quality.values():
        for field in ("baseline", "semantic", "absolute_change"):
            row[field] = float(row[field])
    return benchmark, effort, quality


def document(width, height, title, description, body):
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["white"]}"/>',
            f'<style>text{{font-family:Arial,sans-serif;fill:{COLORS["ink"]}}}.title{{font-size:25px;font-weight:700}}.subtitle{{font-size:14px;fill:{COLORS["muted"]}}}.heading{{font-size:17px;font-weight:700}}.label{{font-size:13px;font-weight:600}}.small{{font-size:12px;fill:{COLORS["muted"]}}}.value{{font-size:13px;font-weight:700}}.big{{font-size:29px;font-weight:700}}</style>',
            *body,
            "</svg>",
        ]
    )


def quality_plot(quality, width=950, height=570):
    metrics = [("precision", "Précision"), ("recall", "Rappel"), ("f1_score", "F1")]
    values = [quality[key][pipeline] for key, _ in metrics for pipeline in ("baseline", "semantic")]
    axis_min = max(0.0, min(values) - 0.02)
    axis_max = min(1.01, max(values) + 0.01)
    left, right = 190, 870

    def scale(value):
        return left + (value - axis_min) / (axis_max - axis_min) * (right - left)

    body = [
        '<text x="475" y="38" text-anchor="middle" class="title">Qualité du matching d’entités</text>',
        '<text x="475" y="64" text-anchor="middle" class="subtitle">Comparaison sur la même vérité terrain · axe resserré et valeurs affichées</text>',
    ]
    for tick in range(5):
        value = axis_min + (axis_max - axis_min) * tick / 4
        x = scale(value)
        body.extend(
            [
                f'<line x1="{x:.1f}" y1="95" x2="{x:.1f}" y2="445" stroke="{COLORS["grid"]}"/>',
                f'<text x="{x:.1f}" y="470" text-anchor="middle" class="small">{value:.3f}</text>',
            ]
        )
    for index, (key, label) in enumerate(metrics):
        y = 150 + index * 115
        baseline = quality[key]["baseline"]
        semantic = quality[key]["semantic"]
        body.extend(
            [
                f'<text x="165" y="{y + 5}" text-anchor="end" class="heading">{label}</text>',
                f'<line x1="{scale(baseline):.1f}" y1="{y}" x2="{scale(semantic):.1f}" y2="{y}" stroke="{COLORS["grid"]}" stroke-width="5"/>',
                f'<circle cx="{scale(baseline):.1f}" cy="{y}" r="9" fill="{COLORS["baseline"]}"/>',
                f'<text x="{scale(baseline):.1f}" y="{y - 18}" text-anchor="middle" class="value">{baseline:.3f}</text>',
                f'<rect x="{scale(semantic) - 9:.1f}" y="{y - 9}" width="18" height="18" fill="{COLORS["semantic"]}"/>',
                f'<text x="{scale(semantic):.1f}" y="{y + 30}" text-anchor="middle" class="value">{semantic:.3f}</text>',
            ]
        )
    body.extend(
        [
            f'<circle cx="330" cy="520" r="7" fill="{COLORS["baseline"]}"/>',
            '<text x="345" y="524" class="label">Baseline</text>',
            f'<rect x="500" y="513" width="14" height="14" fill="{COLORS["semantic"]}"/>',
            '<text x="522" y="524" class="label">Sémantique</text>',
            '<text x="475" y="497" text-anchor="middle" class="small">Score de 0 à 1</text>',
        ]
    )
    return document(width, height, "Qualité du matching d’entités", "Comparaison de la précision, du rappel et du F1.", body)


def error_plot(quality, width=900, height=560):
    metrics = [("false_positives", "Faux positifs"), ("false_negatives", "Faux négatifs")]
    maximum = max(quality[key][pipeline] for key, _ in metrics for pipeline in ("baseline", "semantic"))
    axis_max = max(5, ((int(maximum) + 4) // 5) * 5)
    left, top, chart_width, chart_height = 100, 100, 720, 330
    body = [
        '<text x="450" y="38" text-anchor="middle" class="title">Erreurs de rapprochement</text>',
        '<text x="450" y="64" text-anchor="middle" class="subtitle">La sémantique supprime les mauvaises associations, sans récupérer les liens manqués</text>',
    ]
    for tick in range(6):
        value = axis_max * tick / 5
        y = top + chart_height - value / axis_max * chart_height
        body.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="small">{value:.0f}</text>',
            ]
        )
    centers = [300, 620]
    for index, (key, label) in enumerate(metrics):
        for offset, pipeline in ((-48, "baseline"), (48, "semantic")):
            value = quality[key][pipeline]
            bar_height = value / axis_max * chart_height
            x = centers[index] + offset - 34
            y = top + chart_height - bar_height
            body.extend(
                [
                    f'<rect x="{x}" y="{y:.1f}" width="68" height="{bar_height:.1f}" fill="{COLORS[pipeline]}"/>',
                    f'<text x="{x + 34}" y="{max(y - 8, 88):.1f}" text-anchor="middle" class="value">{value:.0f}</text>',
                ]
            )
        body.append(f'<text x="{centers[index]}" y="465" text-anchor="middle" class="heading">{label}</text>')
    body.extend(
        [
            f'<rect x="315" y="510" width="15" height="15" fill="{COLORS["baseline"]}"/>',
            '<text x="338" y="522" class="label">Baseline</text>',
            f'<rect x="490" y="510" width="15" height="15" fill="{COLORS["semantic"]}"/>',
            '<text x="513" y="522" class="label">Sémantique</text>',
            '<text x="28" y="275" text-anchor="middle" class="small" transform="rotate(-90 28 275)">Nombre de paires</text>',
        ]
    )
    return document(width, height, "Erreurs de rapprochement", "Comparaison des faux positifs et faux négatifs.", body)


def performance_plot(benchmark, width=1050, height=590):
    performance = benchmark["performance"]
    wall = {pipeline: performance[pipeline]["wall_time_seconds"]["median"] * 1000 for pipeline in ("baseline", "semantic")}
    memory = {pipeline: performance[pipeline]["python_peak_memory_bytes"]["median"] / 1024 for pipeline in ("baseline", "semantic")}
    body = [
        '<text x="525" y="38" text-anchor="middle" class="title">Coût technique médian</text>',
        '<text x="525" y="64" text-anchor="middle" class="subtitle">30 exécutions mesurées après 5 préchauffages</text>',
    ]
    panels = [
        ("Temps réel", wall, "ms", 100, 120, 360, 330),
        ("Pic mémoire Python", memory, "KiB", 590, 120, 360, 330),
    ]
    for title, values, unit, left, top, chart_width, chart_height in panels:
        maximum = max(values.values()) * 1.15
        body.append(f'<text x="{left + chart_width / 2}" y="100" text-anchor="middle" class="heading">{title}</text>')
        for tick in range(5):
            value = maximum * tick / 4
            y = top + chart_height - value / maximum * chart_height
            body.extend(
                [
                    f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="{COLORS["grid"]}"/>',
                    f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" class="small">{value:.0f}</text>',
                ]
            )
        for index, pipeline in enumerate(("baseline", "semantic")):
            value = values[pipeline]
            bar_height = value / maximum * chart_height
            x = left + 65 + index * 170
            y = top + chart_height - bar_height
            body.extend(
                [
                    f'<rect x="{x}" y="{y:.1f}" width="90" height="{bar_height:.1f}" fill="{COLORS[pipeline]}"/>',
                    f'<text x="{x + 45}" y="{y - 9:.1f}" text-anchor="middle" class="value">{value:.1f} {unit}</text>',
                    f'<text x="{x + 45}" y="480" text-anchor="middle" class="label">{pipeline.capitalize()}</text>',
                ]
            )
    body.extend(
        [
            f'<text x="300" y="540" text-anchor="middle" class="heading">× {performance["semantic_to_baseline_wall_time_ratio"]:.2f} en temps</text>',
            f'<text x="770" y="540" text-anchor="middle" class="heading">× {performance["semantic_to_baseline_python_memory_ratio"]:.2f} en mémoire Python</text>',
        ]
    )
    return document(width, height, "Coût technique médian", "Temps réel et mémoire Python médians des deux pipelines.", body)


def dashboard(benchmark, effort, quality, width=1150, height=800):
    performance = benchmark["performance"]
    f1_gain = quality["f1_score"]["absolute_change"]
    body = [
        '<text x="575" y="38" text-anchor="middle" class="title">Baseline vs architecture sémantique</text>',
        '<text x="575" y="64" text-anchor="middle" class="subtitle">Même environnement · mêmes données · même vérité terrain</text>',
        f'<text x="150" y="128" text-anchor="middle" class="big">+{f1_gain:.3f}</text>',
        '<text x="150" y="151" text-anchor="middle" class="small">gain absolu de F1</text>',
        f'<text x="430" y="128" text-anchor="middle" class="big">{int(quality["false_positives"]["baseline"])} → {int(quality["false_positives"]["semantic"])}</text>',
        '<text x="430" y="151" text-anchor="middle" class="small">faux positifs</text>',
        f'<text x="720" y="128" text-anchor="middle" class="big">× {performance["semantic_to_baseline_wall_time_ratio"]:.2f}</text>',
        '<text x="720" y="151" text-anchor="middle" class="small">temps médian</text>',
        f'<text x="1000" y="128" text-anchor="middle" class="big">{effort["semantic_per_integration"]["human_validations"]}</text>',
        '<text x="1000" y="151" text-anchor="middle" class="small">validations humaines</text>',
        '<text x="300" y="220" text-anchor="middle" class="heading">Qualité globale</text>',
        '<text x="850" y="220" text-anchor="middle" class="heading">Effort par intégration</text>',
    ]
    for index, (metric, label) in enumerate((("precision", "Précision"), ("recall", "Rappel"), ("f1_score", "F1"))):
        y = 270 + index * 90
        body.append(f'<text x="115" y="{y + 5}" class="label">{label}</text>')
        for pipeline, y_offset in (("baseline", -9), ("semantic", 11)):
            value = quality[metric][pipeline]
            body.extend(
                [
                    f'<line x1="210" y1="{y + y_offset}" x2="{210 + value * 320:.1f}" y2="{y + y_offset}" stroke="{COLORS[pipeline]}" stroke-width="13"/>',
                    f'<text x="550" y="{y + y_offset + 4}" class="small">{value:.3f}</text>',
                ]
            )
    baseline_effort = effort["baseline_per_integration"]
    semantic_effort = effort["semantic_per_integration"]
    effort_rows = [
        ("Mappings manuels baseline", baseline_effort["manual_schema_mappings"], COLORS["baseline"]),
        ("Règles manuelles baseline", baseline_effort["manual_transformation_rules"], COLORS["baseline"]),
        ("Mappings automatiques", semantic_effort["automatic_schema_mappings"], COLORS["semantic"]),
        ("Validations humaines", semantic_effort["human_validations"], COLORS["warning"]),
    ]
    maximum = max(value for _, value, _ in effort_rows)
    for index, (label, value, color) in enumerate(effort_rows):
        y = 260 + index * 67
        body.extend(
            [
                f'<text x="680" y="{y + 5}" class="label">{label}</text>',
                f'<rect x="890" y="{y - 13}" width="{150 * value / maximum:.1f}" height="24" fill="{color}"/>',
                f'<text x="{900 + 150 * value / maximum:.1f}" y="{y + 5}" class="value">{value}</text>',
            ]
        )
    body.extend(
        [
            f'<line x1="75" y1="590" x2="1075" y2="590" stroke="{COLORS["grid"]}"/>',
            '<text x="575" y="635" text-anchor="middle" class="heading">Compromis observé</text>',
            '<text x="575" y="672" text-anchor="middle" class="label">La sémantique élimine les 9 associations incorrectes et améliore le F1,</text>',
            f'<text x="575" y="698" text-anchor="middle" class="label">mais demande 2 validations et un temps médian multiplié par {performance["semantic_to_baseline_wall_time_ratio"]:.2f}.</text>',
            '<text x="575" y="752" text-anchor="middle" class="subtitle">Le coût initial du modèle sémantique est comptabilisé séparément de l’effort par source.</text>',
        ]
    )
    return document(width, height, "Baseline vs architecture sémantique", "Tableau de bord comparant qualité, erreurs, performance et effort.", body)


def run():
    benchmark, effort, quality = load_results()
    outputs = {
        "quality_comparison.svg": quality_plot(quality),
        "error_comparison.svg": error_plot(quality),
        "performance_comparison.svg": performance_plot(benchmark),
        "comparison_dashboard.svg": dashboard(benchmark, effort, quality),
    }
    PLOTS.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        path = PLOTS / filename
        path.write_text(content, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    run()
