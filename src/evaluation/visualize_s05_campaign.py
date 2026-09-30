"""Generate S05 and S01-S05 campaign comparison PNGs."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2"


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def centered(draw, text, x, y, selected_font, fill="#172033"):
    width = draw.textbbox((0, 0), text, font=selected_font)[2]
    draw.text((x - width / 2, y), text, font=selected_font, fill=fill)


def draw_s05():
    payload = json.loads((RESULTS / "S05/summary.json").read_text(encoding="utf-8"))
    architectures = payload["architectures"]
    image = Image.new("RGB", (1600, 1020), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red, blue = "#16a34a", "#f59e0b", "#dc2626", "#2563eb"
    centered(draw, "S05 — conflit entre nom et valeurs", 800, 35, font(40, True))
    centered(draw, "customer_id contient 70 % de tickets et 30 % de clients", 800, 92, font(22), muted)

    series = [
        ("A0", architectures["A0"]["value_quality"]["f1_score"], 0, "3 règles"),
        ("A1", architectures["A1"]["value_quality"]["f1_score"], 70, "aucune alerte"),
        ("A2 avant", architectures["A2"]["before_adaptation"]["value_quality"]["f1_score"], 70, "statique"),
        ("A2 après", architectures["A2"]["after_adaptation"]["value_quality"]["f1_score"], 0, "3 adaptations"),
        ("A3", None, 0, "1 revue"),
    ]
    baseline = 650
    draw.line((120, baseline, 1480, baseline), fill=ink, width=2)
    for index, (label, f1, errors, detail) in enumerate(series):
        x = 220 + index * 290
        if f1 is None:
            height, color, value = 260, orange, "REVUE"
        else:
            height, color, value = int(f1 * 360), green if f1 == 1 else red, f"F1 {f1:.1f}"
        draw.rectangle((x - 78, baseline - height, x + 78, baseline), fill=color)
        centered(draw, value, x, baseline - height / 2 - 12, font(21, True), "white")
        centered(draw, label, x, 680, font(20, True), ink)
        centered(draw, f"{errors} erreurs silencieuses", x, 720, font(16), red if errors else green)
        centered(draw, detail, x, 755, font(16), muted)

    draw.rounded_rectangle((150, 830, 1450, 955), radius=8, fill="#eff6ff")
    centered(draw, "Le score brut A3 favorise Customer.identifier, mais sa marge de 0,009 impose une revue.", 800, 855, font(22, True), blue)
    centered(draw, "La confiance évite 70 erreurs sans exiger une règle de séparation préalable.", 800, 905, font(19), ink)
    output = RESULTS / "S05/s05_identifier_conflict.png"
    image.save(output)
    return output


def draw_campaign():
    image = Image.new("RGB", (1700, 1100), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red = "#16a34a", "#f59e0b", "#dc2626"
    centered(draw, "Synthèse des scénarios sémantiques S01–S05", 850, 35, font(38, True))
    centered(draw, "Comportement initial ; la flèche indique une correction après adaptation", 850, 88, font(20), muted)

    scenarios = [
        ("S01", "Même nom, sens différent"),
        ("S02", "Noms différents, même sens"),
        ("S03", "Définitions concurrentes"),
        ("S04", "Dérive temporelle"),
        ("S05", "Nom contredit par les valeurs"),
    ]
    architectures = ["A0", "A1", "A2", "A3"]
    states = {
        "A0": [("Correct", green)] * 5,
        "A1": [("Revue", orange), ("Revue", orange), ("Revue", orange), ("Revue", orange), ("Dangereux", red)],
        "A2": [("Correct", green), ("Correct", green), ("Correct", green), ("Erreur → correct", orange), ("Erreur → correct", orange)],
        "A3": [("Revue", orange), ("Correct", green), ("Correct", green), ("Revue", orange), ("Revue", orange)],
    }
    left, top, cell_w, cell_h = 470, 235, 285, 135
    for index, (scenario, title) in enumerate(scenarios):
        x = left + index * cell_w
        centered(draw, scenario, x + cell_w / 2, 145, font(22, True), ink)
        centered(draw, title, x + cell_w / 2, 180, font(14), muted)
    for row_index, architecture in enumerate(architectures):
        y = top + row_index * cell_h
        draw.text((115, y + 42), architecture, font=font(25, True), fill=ink)
        subtitles = {"A0": "ETL manuel", "A1": "Métadonnées", "A2": "Déclaratif", "A3": "Adaptatif"}
        draw.text((180, y + 47), subtitles[architecture], font=font(17), fill=muted)
        for column_index, (label, color) in enumerate(states[architecture]):
            x = left + column_index * cell_w
            draw.rounded_rectangle((x + 18, y + 15, x + cell_w - 18, y + cell_h - 15), radius=8, fill=color)
            centered(draw, label, x + cell_w / 2, y + 52, font(18, True), "white")

    draw.rounded_rectangle((150, 835, 1550, 1025), radius=8, fill="#eff6ff")
    centered(draw, "Lecture scientifique", 850, 860, font(23, True), "#2563eb")
    centered(draw, "A0 est exact lorsque toutes les règles sont connues, mais son effort est manuel.", 850, 905, font(18), ink)
    centered(draw, "A2 est robuste aux cas déclarés, mais S04 et S05 exigent une adaptation explicite.", 850, 945, font(18), ink)
    centered(draw, "A3 automatise les équivalences claires et place les ambiguïtés en revue.", 850, 985, font(18), ink)
    output = RESULTS / "semantic_scenarios_s01_s05.png"
    image.save(output)
    return output


def run():
    for output in (draw_s05(), draw_campaign()):
        print(output)


if __name__ == "__main__":
    run()
