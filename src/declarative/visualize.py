"""Generate explanatory PNG visuals for A2 on P00."""

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
A2_RESULTS = ROOT / "results" / "benchmark_v2" / "P00" / "A2"
PLOTS = A2_RESULTS / "plots"


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def centered(draw, text, x, y, selected_font, fill="#172033"):
    width = draw.textbbox((0, 0), text, font=selected_font)[2]
    draw.text((x - width / 2, y), text, font=selected_font, fill=fill)


def load_quality():
    paths = {
        "A0": ROOT / "results/baseline/baseline_evaluation.json",
        "A1": ROOT / "results/benchmark_v2/P00/A1/metrics.json",
        "A2": A2_RESULTS / "metrics.json",
        "A3": ROOT / "results/semantic/pipeline/semantic_evaluation.json",
    }
    data = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    return {
        "A0": data["A0"]["overall"],
        "A1": data["A1"]["entity_quality"],
        "A2": data["A2"]["entity_quality"],
        "A3": data["A3"]["overall"],
    }, data["A2"]


def dashboard(quality, metrics):
    image = Image.new("RGB", (1600, 1040), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    blue, green, orange, purple = "#2563eb", "#16a34a", "#f59e0b", "#7c3aed"
    centered(draw, "P00 — positionnement d’A2 dans le benchmark", 800, 35, font(40, True))
    centered(draw, "Même qualité nominale, mécanismes d’intégration différents", 800, 92, font(22), muted)

    labels = [
        ("A0", "ETL manuel", blue),
        ("A1", "Métadonnées techniques", green),
        ("A2", "Sémantique déclarative", orange),
        ("A3", "Sémantique adaptative", purple),
    ]
    left, top, width, height = 140, 210, 1320, 430
    for tick in range(6):
        value = tick / 5
        y = top + height - value * height
        draw.line((left, y, left + width, y), fill="#e5e7eb", width=1)
        draw.text((75, y - 11), f"{value:.1f}", font=font(17), fill=muted)
    draw.line((left, top + height, left + width, top + height), fill=ink, width=2)
    for index, (name, subtitle, color) in enumerate(labels):
        center = left + width * (index + 0.5) / 4
        value = quality[name]["f1_score"]
        bar_height = value * height
        y0 = top + height - bar_height
        draw.rectangle((center - 60, y0, center + 60, top + height), fill=color)
        centered(draw, f"{value:.3f}", center, y0 - 35, font(21, True), ink)
        centered(draw, name, center, 670, font(22, True), ink)
        centered(draw, subtitle, center, 707, font(17), muted)

    cards = [
        ("Mappings déclarés", str(metrics["declarative_schema_mappings"])),
        ("Transformations déclarées", str(metrics["declarative_transformations"])),
        ("Faux positifs", str(metrics["entity_quality"]["false_positives"])),
        ("Faux négatifs", str(metrics["entity_quality"]["false_negatives"])),
    ]
    for index, (label, value) in enumerate(cards):
        x = 100 + index * 375
        draw.rounded_rectangle((x, 795, x + 330, 940), radius=9, fill="#fff7ed", outline="#fed7aa")
        centered(draw, value, x + 165, 825, font(35, True), orange)
        centered(draw, label, x + 165, 883, font(18), ink)
    centered(draw, "Les temps ne sont pas comparés ici : A2 n’a pas encore suivi le protocole multi-exécutions.", 800, 982, font(18), muted)
    image.save(PLOTS / "a2_p00_comparison.png")


def p01_before_after():
    image = Image.new("RGB", (1500, 820), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, red, green, orange = "#172033", "#667085", "#dc2626", "#16a34a", "#f59e0b"
    centered(draw, "A2 / P01 — adaptation à une colonne renommée", 750, 35, font(38, True))
    centered(draw, "Une modification YAML restaure le résultat nominal", 750, 90, font(21), muted)

    stages = [
        (210, "Avant adaptation", "ÉCHEC", "mail absent", red),
        (750, "Adaptation", "1", "mapping YAML modifié", orange),
        (1290, "Après adaptation", "0,979", "F1 restauré", green),
    ]
    for index, (x, title, value, subtitle, color) in enumerate(stages):
        draw.ellipse((x - 105, 235, x + 105, 445), fill=color)
        centered(draw, value, x, 305, font(31, True), "white")
        centered(draw, title, x, 490, font(22, True), ink)
        centered(draw, subtitle, x, 530, font(18), muted)
        if index < 2:
            draw.line((x + 125, 340, stages[index + 1][0] - 125, 340), fill=ink, width=4)
            end = stages[index + 1][0] - 125
            draw.polygon([(end, 340), (end - 16, 330), (end - 16, 350)], fill=ink)

    draw.rounded_rectangle((160, 625, 1340, 735), radius=8, fill="#ecfdf5")
    centered(draw, "0 changement du pipeline/moteur · 0 suggestion automatique · 0 score de confiance", 750, 650, font(22, True), green)
    centered(draw, "mail → customer_email_address est explicitement déclaré dans une surcharge YAML versionnée", 750, 692, font(19), ink)
    image.save(ROOT / "results/benchmark_v2/P01/A2/a2_p01_before_after.png")


def p02_before_after():
    image = Image.new("RGB", (1500, 850), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, red, green, orange = "#172033", "#667085", "#dc2626", "#16a34a", "#f59e0b"
    centered(draw, "A2 / P02 — conformité des valeurs pays", 750, 35, font(38, True))
    centered(draw, "Le matching réussit dans les deux cas, la qualité métier change", 750, 90, font(21), muted)

    left, top, width, height = 240, 215, 1020, 390
    for tick in range(6):
        value = tick * 20
        y = top + height - value / 100 * height
        draw.line((left, y, left + width, y), fill="#e5e7eb", width=1)
        draw.text((155, y - 11), f"{value} %", font=font(17), fill=muted)
    bars = [
        (495, 0, "Avant adaptation", "0 / 100 conformes", red),
        (1005, 100, "Après 7 entrées YAML", "100 / 100 conformes", green),
    ]
    for x, value, label, detail, color in bars:
        bar_height = value / 100 * height
        y0 = top + height - bar_height
        if value == 0:
            draw.rectangle((x - 95, top + height - 6, x + 95, top + height), fill=color)
            value_y = top + height - 48
        else:
            draw.rectangle((x - 95, y0, x + 95, top + height), fill=color)
            value_y = y0 - 42
        centered(draw, f"{value} %", x, value_y, font(25, True), ink)
        centered(draw, label, x, 640, font(21, True), ink)
        centered(draw, detail, x, 680, font(18), muted)

    draw.rounded_rectangle((190, 750, 1310, 820), radius=8, fill="#fff7ed")
    centered(draw, "F1 entités inchangé : 0,979 · adaptation limitée au vocabulaire déclaratif", 750, 772, font(21, True), orange)
    image.save(ROOT / "results/benchmark_v2/P02/A2/a2_p02_before_after.png")


def p03_before_after():
    image = Image.new("RGB", (1500, 850), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, red, green, orange = "#172033", "#667085", "#dc2626", "#16a34a", "#f59e0b"
    centered(draw, "A2 / P03 — évolution de la structure du nom", 750, 35, font(38, True))
    centered(draw, "Deux colonnes et une dérivation sont remplacées par un mapping direct", 750, 90, font(21), muted)

    columns = [
        (270, "Schéma initial", ["first_name", "+", "last_name"], orange),
        (750, "Schéma perturbé", ["customer_name"], red),
        (1230, "Après adaptation", ["full_name"], green),
    ]
    for index, (x, title, items, color) in enumerate(columns):
        centered(draw, title, x, 205, font(23, True), ink)
        y = 280
        for item in items:
            if item == "+":
                centered(draw, item, x, y, font(27, True), muted)
                y += 58
                continue
            draw.rounded_rectangle((x - 150, y, x + 150, y + 76), radius=7, fill=color)
            centered(draw, item, x, y + 22, font(21, True), "white")
            y += 100
        if index < 2:
            end = columns[index + 1][0] - 185
            draw.line((x + 185, 365, end, 365), fill=ink, width=4)
            draw.polygon([(end, 365), (end - 16, 355), (end - 16, 375)], fill=ink)

    centered(draw, "ÉCHEC", 750, 525, font(28, True), red)
    centered(draw, "first_name et last_name absents", 750, 568, font(18), muted)
    centered(draw, "F1 = 0,979", 1230, 525, font(28, True), green)
    centered(draw, "qualité nominale restaurée", 1230, 568, font(18), muted)

    draw.rounded_rectangle((170, 675, 1330, 790), radius=8, fill="#fff7ed")
    centered(draw, "4 opérations YAML", 750, 696, font(25, True), orange)
    centered(draw, "2 mappings retirés · 1 mapping ajouté · 1 dérivation retirée · 0 changement du moteur", 750, 744, font(19), ink)
    image.save(ROOT / "results/benchmark_v2/P03/A2/a2_p03_before_after.png")


def p04_scale():
    summary = ROOT / "results/benchmark_v2/P04/A2/scale_summary.csv"
    with summary.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    image = Image.new("RGB", (1500, 900), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, orange, green = "#172033", "#667085", "#f59e0b", "#16a34a"
    centered(draw, "A2 / P04 — passage à l’échelle", 750, 35, font(38, True))
    centered(draw, "Temps médian de 5 exécutions · même modèle déclaratif", 750, 90, font(21), muted)

    maximum = max(float(row["median_seconds"]) for row in rows) * 1.18
    left, top, width, height = 155, 200, 1190, 455
    for tick in range(5):
        value = maximum * tick / 4
        y = top + height - value / maximum * height
        draw.line((left, y, left + width, y), fill="#e5e7eb", width=1)
        draw.text((45, y - 11), f"{value:.3f} s", font=font(17), fill=muted)
    for index, row in enumerate(rows):
        x = left + width * (index + 0.5) / len(rows)
        value = float(row["median_seconds"])
        y0 = top + height - value / maximum * height
        draw.rectangle((x - 82, y0, x + 82, top + height), fill=orange)
        centered(draw, f"{value:.3f} s", x, y0 - 36, font(21, True), ink)
        centered(draw, row["scale"], x, 688, font(23, True), ink)
        centered(draw, f"{int(row['output_rows'])} entités", x, 728, font(18), muted)
        centered(draw, "F1 = 0,979", x, 768, font(18, True), green)
    draw.rounded_rectangle((225, 820, 1275, 875), radius=8, fill="#ecfdf5")
    centered(draw, "0 adaptation déclarative aux trois tailles", 750, 835, font(21, True), green)
    image.save(ROOT / "results/benchmark_v2/P04/A2/a2_p04_scale.png")


def p05_new_source():
    image = Image.new("RGB", (1500, 850), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, red, green, orange = "#172033", "#667085", "#dc2626", "#16a34a", "#f59e0b"
    centered(draw, "A2 / P05 — intégration de la source Loyalty", 750, 35, font(38, True))
    centered(draw, "La découverte technique ne remplace pas la déclaration métier", 750, 90, font(21), muted)

    stages = [
        (220, "Découverte", "loyalty.csv", "détecté", orange),
        (750, "Avant adaptation", "REJET", "source non déclarée", red),
        (1280, "Après adaptation", "1,000", "F1 CRM ↔ Loyalty", green),
    ]
    for index, (x, title, value, detail, color) in enumerate(stages):
        centered(draw, title, x, 210, font(22, True), ink)
        draw.rounded_rectangle((x - 145, 285, x + 145, 425), radius=10, fill=color)
        centered(draw, value, x, 323, font(29, True), "white")
        centered(draw, detail, x, 450, font(18), muted)
        if index < 2:
            end = stages[index + 1][0] - 175
            draw.line((x + 175, 355, end, 355), fill=ink, width=4)
            draw.polygon([(end, 355), (end - 16, 345), (end - 16, 365)], fill=ink)

    cards = [("1", "source ajoutée"), ("5", "mappings YAML"), ("4", "transformations")]
    for index, (value, label) in enumerate(cards):
        x = 260 + index * 490
        draw.rounded_rectangle((x - 165, 575, x + 165, 705), radius=8, fill="#fff7ed", outline="#fed7aa")
        centered(draw, value, x, 596, font(32, True), orange)
        centered(draw, label, x, 650, font(18), ink)
    centered(draw, "80 / 80 relations CRM–Loyalty correctes · 0 changement du pipeline/moteur", 750, 775, font(21, True), green)
    image.save(ROOT / "results/benchmark_v2/P05/A2/a2_p05_new_source.png")


def run():
    quality, metrics = load_quality()
    PLOTS.mkdir(parents=True, exist_ok=True)
    dashboard(quality, metrics)
    p01_before_after()
    p02_before_after()
    p03_before_after()
    p04_scale()
    p05_new_source()
    print(PLOTS / "a2_p00_comparison.png")
    print(ROOT / "results/benchmark_v2/P01/A2/a2_p01_before_after.png")
    print(ROOT / "results/benchmark_v2/P02/A2/a2_p02_before_after.png")
    print(ROOT / "results/benchmark_v2/P03/A2/a2_p03_before_after.png")
    print(ROOT / "results/benchmark_v2/P04/A2/a2_p04_scale.png")
    print(ROOT / "results/benchmark_v2/P05/A2/a2_p05_new_source.png")


if __name__ == "__main__":
    run()
