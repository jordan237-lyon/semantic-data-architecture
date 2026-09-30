"""Render the consolidated S01-S05 benchmark dashboard as PNG."""

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2/semantic_benchmark"


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def centered(draw, text, x, y, selected_font, fill="#172033"):
    width = draw.textbbox((0, 0), text, font=selected_font)[2]
    draw.text((x - width / 2, y), text, font=selected_font, fill=fill)


def run():
    with (RESULTS / "architecture_summary.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    image = Image.new("RGB", (1700, 1120), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    blue, green, orange, red = "#2563eb", "#16a34a", "#f59e0b", "#dc2626"
    centered(draw, "Benchmark sémantique consolidé S01–S05", 850, 35, font(40, True))
    centered(draw, "Qualité normalisée, sécurité et coût d’intervention", 850, 92, font(22), muted)

    baseline = 620
    draw.line((120, baseline, 1580, baseline), fill=ink, width=2)
    for index, row in enumerate(rows):
        x = 265 + index * 390
        initial = float(row["initial_mean_outcome"])
        final = float(row["final_mean_outcome"])
        for offset, value, color, label in ((-72, initial, blue, "Initial"), (72, final, green, "Final")):
            height = int(value * 370)
            draw.rectangle((x - 50 + offset, baseline - height, x + 50 + offset, baseline), fill=color)
            centered(draw, f"{value:.2f}", x + offset, baseline - height - 38, font(20, True), ink)
            centered(draw, label, x + offset, 642, font(15), muted)
        centered(draw, row["architecture"], x, 690, font(27, True), ink)
        centered(draw, f"Sûrs : {row['initial_safe_scenarios']}/5", x, 735, font(18, True), green if row["initial_safe_scenarios"] == "5" else orange)
        centered(draw, f"Erreurs silencieuses : {row['silent_wrong_acceptances']}", x, 775, font(17), red if row["silent_wrong_acceptances"] != "0" else green)
        centered(draw, f"Revues initiales : {row['initial_human_reviews']}", x, 810, font(17), ink)

    centered(draw, "Score moyen normalisé", 850, 865, font(17), muted)
    draw.rounded_rectangle((150, 910, 1550, 1060), radius=8, fill="#eff6ff")
    centered(draw, "Interprétation", 850, 930, font(23, True), blue)
    centered(draw, "A0 : qualité maximale avec règles préalables · A2 : qualité maximale après adaptation", 850, 975, font(18), ink)
    centered(draw, "A3 : meilleur compromis initial sécurité–automatisation · A1 : insuffisant seul pour les ambiguïtés métier", 850, 1015, font(18), ink)

    output = RESULTS / "semantic_benchmark_dashboard.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    run()
