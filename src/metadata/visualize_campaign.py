"""Generate PNG summaries of the A1 campaign (P01-P05)."""

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "benchmark_v2"
PLOTS = RESULTS / "plots"


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def centered(draw, text, x, y, selected_font, fill="#172033"):
    width = draw.textbbox((0, 0), text, font=selected_font)[2]
    draw.text((x - width / 2, y), text, font=selected_font, fill=fill)


def load_rows():
    with (RESULTS / "a1_campaign_summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for key in ("review_columns", "output_rows", "f1_score", "median_seconds"):
            row[key] = float(row[key])
    return rows


def robustness(rows):
    selected = [row for row in rows if row["scenario"] in {"P01", "P02", "P03", "P05"}]
    image = Image.new("RGB", (1500, 930), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, blue, orange, green = "#172033", "#667085", "#2563eb", "#f59e0b", "#16a34a"
    centered(draw, "A1 — robustesse face aux perturbations P01–P05", 750, 34, font(38, True))
    centered(draw, "Même moteur technique, aucune règle spécifique ajoutée", 750, 88, font(21), muted)
    labels = [("P01", "colonne renommée"), ("P02", "format pays"), ("P03", "nom fusionné"), ("P05", "nouvelle source")]
    left, top, width, height = 135, 205, 1230, 430
    for tick in range(6):
        score = tick / 5
        y = top + height - score * height
        draw.line((left, y, left + width, y), fill="#e5e7eb", width=1)
        draw.text((70, y - 12), f"{score:.1f}", font=font(17), fill=muted)
    draw.line((left, top + height, left + width, top + height), fill=ink, width=2)
    for index, row in enumerate(selected):
        center = left + width * (index + 0.5) / len(selected)
        value = row["f1_score"]
        bar_height = value * height
        y0 = top + height - bar_height
        draw.rectangle((center - 58, y0, center + 58, top + height), fill=blue)
        centered(draw, f"{value:.3f}", center, y0 - 35, font(20, True), ink)
        centered(draw, labels[index][0], center, 662, font(19, True), ink)
        centered(draw, labels[index][1], center, 692, font(17), muted)
        centered(draw, f"{int(row['review_columns'])} colonnes en revue", center, 735, font(17), orange)
    draw.rounded_rectangle((135, 800, 1365, 880), radius=8, fill="#ecfdf5")
    centered(draw, "P05 : Loyalty découverte automatiquement — F1 CRM ↔ Loyalty = 1,000", 750, 824, font(22, True), green)
    image.save(PLOTS / "a1_perturbation_robustness.png")


def scale(rows):
    selected = [row for row in rows if row["scenario"] == "P04"]
    image = Image.new("RGB", (1500, 930), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, blue, green = "#172033", "#667085", "#2563eb", "#16a34a"
    centered(draw, "A1 / P04 — comportement au passage à l’échelle", 750, 34, font(38, True))
    centered(draw, "Temps médian de 5 exécutions · qualité du matching stable", 750, 88, font(21), muted)
    left, top, width, height = 150, 200, 1200, 470
    maximum = max(row["median_seconds"] for row in selected) * 1.18
    for tick in range(5):
        value = maximum * tick / 4
        y = top + height - value / maximum * height
        draw.line((left, y, left + width, y), fill="#e5e7eb", width=1)
        draw.text((45, y - 12), f"{value:.3f} s", font=font(17), fill=muted)
    for index, row in enumerate(selected):
        center = left + width * (index + 0.5) / len(selected)
        value = row["median_seconds"]
        bar_height = value / maximum * height
        y0 = top + height - bar_height
        draw.rectangle((center - 82, y0, center + 82, top + height), fill=blue)
        centered(draw, f"{value:.3f} s", center, y0 - 35, font(21, True), ink)
        centered(draw, row["variant"], center, 704, font(22, True), ink)
        centered(draw, f"{int(row['output_rows'])} entités", center, 742, font(18), muted)
        centered(draw, "F1 = 0,979", center, 780, font(18, True), green)
    centered(draw, "Taille du jeu de données", 750, 840, font(20), ink)
    image.save(PLOTS / "a1_scale_performance.png")


def run():
    PLOTS.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    robustness(rows)
    scale(rows)
    print(PLOTS / "a1_perturbation_robustness.png")
    print(PLOTS / "a1_scale_performance.png")


if __name__ == "__main__":
    run()
