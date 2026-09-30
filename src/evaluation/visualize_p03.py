"""Generate the SVG dashboard for P03."""

import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "perturbations" / "p03_merged_name_columns"


def dashboard(result, before):
    mapping = result["semantic"]["perturbed_column_mapping"]
    semantic_status = result["semantic"]["status"]
    semantic_text = "SUCCÈS AUTOMATIQUE" if semantic_status == "success" else "VALIDATION REQUISE"
    semantic_color = "#16a34a" if semantic_status == "success" else "#f59e0b"
    quality = result["semantic"].get("entity_quality", {})
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="680" viewBox="0 0 1080 680" role="img" aria-labelledby="t d">
<title id="t">P03 — fusion des colonnes de nom</title><desc id="d">Réaction de la baseline et du pipeline sémantique à une modification structurelle du CRM.</desc>
<rect width="1080" height="680" fill="white"/><style>text{{font-family:Arial,sans-serif;fill:#172033}}.title{{font-size:25px;font-weight:700}}.sub{{font-size:14px;fill:#667085}}.head{{font-size:18px;font-weight:700}}.big{{font-size:29px;font-weight:700}}.lab{{font-size:13px;font-weight:600}}</style>
<text x="540" y="42" text-anchor="middle" class="title">P03 — deux colonnes deviennent un attribut métier</text>
<text x="540" y="70" text-anchor="middle" class="sub">CRM : first_name + last_name → customer_name</text>
<rect x="110" y="105" width="190" height="55" fill="#dbeafe"/><text x="205" y="138" text-anchor="middle" class="lab">first_name</text>
<rect x="320" y="105" width="190" height="55" fill="#dbeafe"/><text x="415" y="138" text-anchor="middle" class="lab">last_name</text>
<text x="550" y="140" text-anchor="middle" class="big">→</text><rect x="600" y="105" width="300" height="55" fill="#dcfce7"/><text x="750" y="138" text-anchor="middle" class="head">customer_name</text>
<text x="270" y="225" text-anchor="middle" class="head">Baseline manuelle</text><text x="810" y="225" text-anchor="middle" class="head">Pipeline sémantique</text>
<rect x="75" y="255" width="390" height="175" fill="#dcfce7"/><text x="270" y="305" text-anchor="middle" class="big" fill="#16a34a">SUCCÈS APRÈS ADAPTATION</text>
<text x="270" y="345" text-anchor="middle" class="lab">Avant : {escape(before['baseline']['error'])}</text><text x="270" y="377" text-anchor="middle" class="sub">Après : branche Python pour customer_name</text><text x="270" y="405" text-anchor="middle" class="sub">1 règle manuelle supplémentaire</text>
<rect x="615" y="255" width="390" height="175" fill="#dcfce7"/><text x="810" y="310" text-anchor="middle" class="big" fill="{semantic_color}">{semantic_text}</text>
<text x="810" y="350" text-anchor="middle" class="lab">{escape(mapping['semantic_attribute'])}</text><text x="810" y="382" text-anchor="middle" class="sub">score {float(mapping['total_score']):.3f} · marge {float(mapping['score_margin']):.3f}</text>
<line x1="75" y1="480" x2="1005" y2="480" stroke="#d8dee9"/>
<text x="540" y="530" text-anchor="middle" class="head">Effort d’adaptation</text><text x="270" y="575" text-anchor="middle" class="lab">Baseline : 1 règle Python · total 11 règles</text><text x="810" y="575" text-anchor="middle" class="lab">Sémantique : 0 modification · 0 validation supplémentaire</text>
<text x="540" y="625" text-anchor="middle" class="head">F1 : baseline {result['baseline']['entity_quality']['f1_score']:.3f} · sémantique {quality.get('f1_score', 0):.3f}</text><text x="540" y="653" text-anchor="middle" class="sub">Les deux produisent les résultats attendus après adaptation de la baseline.</text></svg>'''


def run():
    result = json.loads((RESULTS / "results.json").read_text(encoding="utf-8"))
    before = json.loads(
        (RESULTS / "before_adaptation" / "results.json").read_text(encoding="utf-8")
    )
    plots = RESULTS / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    path = plots / "p03_dashboard.svg"
    path.write_text(dashboard(result, before), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    run()
