"""Generate explanatory SVG visuals for perturbation P01."""

import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIO = "p01_renamed_column"
RESULTS = ROOT / "results" / "perturbations" / SCENARIO
PLOTS = RESULTS / "plots"

COLORS = {
    "baseline": "#64748b",
    "semantic": "#2563eb",
    "success": "#16a34a",
    "review": "#f59e0b",
    "failure": "#dc2626",
    "ink": "#172033",
    "muted": "#667085",
    "grid": "#d8dee9",
    "soft_blue": "#dbeafe",
    "soft_orange": "#fef3c7",
    "soft_green": "#dcfce7",
    "soft_red": "#fee2e2",
    "white": "#ffffff",
}


def load_result():
    return json.loads((RESULTS / "results.json").read_text(encoding="utf-8"))


def document(width, height, title, description, body):
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            f'<rect width="100%" height="100%" fill="{COLORS["white"]}"/>',
            f'<style>text{{font-family:Arial,sans-serif;fill:{COLORS["ink"]}}}.title{{font-size:25px;font-weight:700}}.subtitle{{font-size:14px;fill:{COLORS["muted"]}}}.heading{{font-size:18px;font-weight:700}}.label{{font-size:13px;font-weight:600}}.small{{font-size:12px;fill:{COLORS["muted"]}}}.value{{font-size:14px;font-weight:700}}.big{{font-size:30px;font-weight:700}}</style>',
            *body,
            "</svg>",
        ]
    )


def adaptation_outcome(result, width=1050, height=590):
    mapping = result["semantic"]["perturbed_column_mapping"]
    semantic_succeeded = result["semantic"]["status"] == "success"
    semantic_fill = COLORS["soft_green"] if semantic_succeeded else COLORS["soft_orange"]
    semantic_color = COLORS["success"] if semantic_succeeded else COLORS["review"]
    semantic_status = "SUCCÈS APRÈS VALIDATION" if semantic_succeeded else "À VALIDER"
    body = [
        '<text x="525" y="38" text-anchor="middle" class="title">P01 — réaction au renommage d’une colonne</text>',
        '<text x="525" y="65" text-anchor="middle" class="subtitle">Même contenu, seul le nom physique de la colonne change</text>',
        f'<rect x="250" y="95" width="220" height="55" fill="{COLORS["soft_blue"]}"/>',
        '<text x="360" y="128" text-anchor="middle" class="heading">support.mail</text>',
        f'<line x1="485" y1="122" x2="555" y2="122" stroke="{COLORS["semantic"]}" stroke-width="3"/>',
        f'<path d="M 545 115 L 555 122 L 545 129" fill="none" stroke="{COLORS["semantic"]}" stroke-width="3"/>',
        f'<rect x="570" y="95" width="250" height="55" fill="{COLORS["soft_blue"]}"/>',
        '<text x="695" y="128" text-anchor="middle" class="heading">customer_email_address</text>',
        '<text x="275" y="215" text-anchor="middle" class="heading">Baseline manuelle</text>',
        '<text x="775" y="215" text-anchor="middle" class="heading">Moteur sémantique</text>',
        f'<rect x="80" y="245" width="390" height="185" fill="{COLORS["soft_red"]}"/>',
        f'<text x="275" y="302" text-anchor="middle" class="big" fill="{COLORS["failure"]}">ÉCHEC</text>',
        '<text x="275" y="342" text-anchor="middle" class="label">KeyError: mail</text>',
        '<text x="275" y="375" text-anchor="middle" class="small">Le nom de colonne est codé dans transform.py</text>',
        '<text x="275" y="405" text-anchor="middle" class="value">Adaptation : modification du code</text>',
        f'<rect x="580" y="245" width="390" height="185" fill="{semantic_fill}"/>',
        f'<text x="775" y="295" text-anchor="middle" class="big" fill="{semantic_color}">{semantic_status}</text>',
        f'<text x="775" y="335" text-anchor="middle" class="label">→ {escape(mapping["semantic_attribute"])}</text>',
        f'<text x="775" y="368" text-anchor="middle" class="small">Score {float(mapping["total_score"]):.3f} · marge {float(mapping["score_margin"]):.3f}</text>',
        '<text x="775" y="405" text-anchor="middle" class="value">Adaptation : une décision humaine</text>',
        f'<line x1="80" y1="475" x2="970" y2="475" stroke="{COLORS["grid"]}"/>',
        '<text x="525" y="520" text-anchor="middle" class="heading">Premier constat</text>',
        '<text x="525" y="552" text-anchor="middle" class="label">La baseline ne démarre plus ; la sémantique trouve le bon sens mais demande confirmation.</text>',
    ]
    return document(width, height, "P01 — réaction au renommage", "Comparaison de l'échec de la baseline et de la validation demandée par le moteur sémantique.", body)


def mapping_confidence(result, width=950, height=610):
    mapping = result["semantic"]["perturbed_column_mapping"]
    components = [
        ("Nom", float(mapping["name_score"]), COLORS["baseline"]),
        ("Type", float(mapping["type_score"]), COLORS["semantic"]),
        ("Valeurs", float(mapping["value_score"]), COLORS["success"]),
        ("Total", float(mapping["total_score"]), COLORS["review"]),
    ]
    body = [
        '<text x="475" y="38" text-anchor="middle" class="title">Pourquoi le mapping demande une validation</text>',
        '<text x="475" y="65" text-anchor="middle" class="subtitle">customer_email_address → Customer.email</text>',
    ]
    left, top, chart_width = 210, 120, 620
    for tick in range(6):
        value = tick / 5
        x = left + value * chart_width
        body.extend(
            [
                f'<line x1="{x}" y1="100" x2="{x}" y2="400" stroke="{COLORS["grid"]}"/>',
                f'<text x="{x}" y="430" text-anchor="middle" class="small">{value:.1f}</text>',
            ]
        )
    for index, (label, value, color) in enumerate(components):
        y = top + index * 70
        body.extend(
            [
                f'<text x="185" y="{y + 5}" text-anchor="end" class="heading">{label}</text>',
                f'<rect x="{left}" y="{y - 14}" width="{value * chart_width:.1f}" height="28" fill="{color}"/>',
                f'<text x="{left + value * chart_width + 12:.1f}" y="{y + 5}" class="value">{value:.3f}</text>',
            ]
        )
    margin = float(mapping["score_margin"])
    body.extend(
        [
            '<text x="475" y="485" text-anchor="middle" class="heading">Le score est suffisant, mais la marge impose une validation</text>',
            f'<text x="300" y="530" text-anchor="middle" class="big">{float(mapping["total_score"]):.3f}</text>',
            '<text x="300" y="555" text-anchor="middle" class="small">score total ≥ 0,85</text>',
            f'<text x="650" y="530" text-anchor="middle" class="big" fill="{COLORS["review"]}">{margin:.3f}</text>',
            '<text x="650" y="555" text-anchor="middle" class="small">marge &lt; 0,10</text>',
            f'<text x="475" y="595" text-anchor="middle" class="label">Second candidat : {escape(mapping["second_candidate"])} ({float(mapping["second_score"]):.3f}) · validation enregistrée</text>',
        ]
    )
    return document(width, height, "Pourquoi le mapping demande une validation", "Décomposition des scores et comparaison de la marge avec le seuil.", body)


def p01_dashboard(result, width=1100, height=760):
    mapping = result["semantic"]["perturbed_column_mapping"]
    semantic_succeeded = result["semantic"]["status"] == "success"
    semantic_label = "Succès" if semantic_succeeded else "Revue"
    semantic_color = COLORS["success"] if semantic_succeeded else COLORS["review"]
    body = [
        f'<text x="550" y="38" text-anchor="middle" class="title">P01 — bilan {"après validation" if semantic_succeeded else "avant adaptation"}</text>',
        '<text x="550" y="64" text-anchor="middle" class="subtitle">Renommage : mail → customer_email_address</text>',
        f'<text x="175" y="135" text-anchor="middle" class="big" fill="{COLORS["failure"]}">Échec</text>',
        '<text x="175" y="162" text-anchor="middle" class="small">baseline</text>',
        f'<text x="450" y="135" text-anchor="middle" class="big" fill="{semantic_color}">{semantic_label}</text>',
        '<text x="450" y="162" text-anchor="middle" class="small">sémantique</text>',
        f'<text x="725" y="135" text-anchor="middle" class="big">{float(mapping["total_score"]):.3f}</text>',
        '<text x="725" y="162" text-anchor="middle" class="small">score du bon mapping</text>',
        '<text x="975" y="135" text-anchor="middle" class="big">0</text>',
        '<text x="975" y="162" text-anchor="middle" class="small">modification appliquée</text>',
        '<text x="300" y="230" text-anchor="middle" class="heading">Chemin baseline</text>',
        f'<rect x="90" y="260" width="170" height="65" fill="{COLORS["soft_blue"]}"/>',
        '<text x="175" y="298" text-anchor="middle" class="label">Colonne renommée</text>',
        f'<line x1="270" y1="292" x2="330" y2="292" stroke="{COLORS["failure"]}" stroke-width="3"/>',
        f'<rect x="340" y="260" width="170" height="65" fill="{COLORS["soft_red"]}"/>',
        '<text x="425" y="286" text-anchor="middle" class="label">Recherche mail</text>',
        '<text x="425" y="307" text-anchor="middle" class="small">KeyError</text>',
        '<text x="300" y="365" text-anchor="middle" class="value">Résultat : changement de code nécessaire</text>',
        '<text x="800" y="230" text-anchor="middle" class="heading">Chemin sémantique</text>',
        f'<rect x="590" y="260" width="150" height="65" fill="{COLORS["soft_blue"]}"/>',
        '<text x="665" y="286" text-anchor="middle" class="label">Profil e-mail</text>',
        '<text x="665" y="307" text-anchor="middle" class="small">type + valeurs</text>',
        f'<line x1="750" y1="292" x2="800" y2="292" stroke="{COLORS["semantic"]}" stroke-width="3"/>',
        f'<rect x="810" y="260" width="200" height="65" fill="{COLORS["soft_orange"]}"/>',
        '<text x="910" y="286" text-anchor="middle" class="label">Customer.email</text>',
        f'<text x="910" y="307" text-anchor="middle" class="small">marge {float(mapping["score_margin"]):.3f}</text>',
        f'<text x="800" y="365" text-anchor="middle" class="value">Résultat : {"pipeline exécuté après validation" if semantic_succeeded else "une validation nécessaire"}</text>',
        f'<line x1="75" y1="420" x2="1025" y2="420" stroke="{COLORS["grid"]}"/>',
        '<text x="550" y="470" text-anchor="middle" class="heading">Nature de l’effort d’adaptation</text>',
        f'<rect x="185" y="510" width="260" height="35" fill="{COLORS["failure"]}"/>',
        '<text x="315" y="533" text-anchor="middle" font-size="13" font-weight="700" fill="white">Baseline : modifier le programme</text>',
        f'<rect x="655" y="510" width="260" height="35" fill="{COLORS["review"]}"/>',
        '<text x="785" y="533" text-anchor="middle" font-size="13" font-weight="700" fill="white">Sémantique : confirmer le sens</text>',
        '<text x="550" y="610" text-anchor="middle" class="heading">Conclusion provisoire</text>',
        '<text x="550" y="646" text-anchor="middle" class="label">Le moteur ne s’adapte pas encore sans intervention, mais il transforme une panne technique</text>',
        '<text x="550" y="672" text-anchor="middle" class="label">en une décision métier explicite, traçable et sans modification de code.</text>',
        f'<text x="550" y="724" text-anchor="middle" class="subtitle">{"Qualité finale : précision 1,000 · rappel 0,958 · F1 0,979." if semantic_succeeded else "La qualité finale sera mesurée après validation humaine."}</text>',
    ]
    return document(width, height, "P01 — bilan avant adaptation", "Tableau de bord du premier scénario de perturbation avant validation humaine.", body)


def run():
    result = load_result()
    outputs = {
        "p01_dashboard.svg": p01_dashboard(result),
        "adaptation_outcome.svg": adaptation_outcome(result),
        "mapping_confidence.svg": mapping_confidence(result),
    }
    PLOTS.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        path = PLOTS / filename
        path.write_text(content, encoding="utf-8")
        print(path)


if __name__ == "__main__":
    run()
