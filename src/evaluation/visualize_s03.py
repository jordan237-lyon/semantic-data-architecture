"""Generate the S03 gross-versus-net semantic comparison as PNG."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2/S03"


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
    payload = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    summary = payload["architectures"]
    checks = payload["dataset_checks"]
    image = Image.new("RGB", (1600, 1040), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red, blue = "#16a34a", "#f59e0b", "#dc2626", "#2563eb"

    centered(draw, "S03 — définitions métier concurrentes", 800, 35, font(40, True))
    centered(draw, "Revenu brut ≠ revenu net · granularité client-mois", 800, 92, font(22), muted)

    architectures = ["A0", "A1", "A2", "A3"]
    subtitles = ["Manuel", "Métadonnées", "Déclaratif", "Adaptatif"]
    for index, architecture in enumerate(architectures):
        metrics = summary[architecture]["semantic_quality"]
        x = 235 + index * 380
        accepted, review = metrics["accepted_correct"], metrics["review_mappings"]
        centered(draw, architecture, x, 175, font(28, True), ink)
        centered(draw, subtitles[index], x, 215, font(17), muted)
        color = green if accepted == 2 else orange
        value = f"{accepted}/2 corrects" if accepted else f"{review} en revue"
        draw.rectangle((x - 90, 295, x + 90, 625), fill=color)
        centered(draw, value, x, 438, font(21, True), "white")
        centered(draw, f"F1 : {metrics['f1_score']:.2f}", x, 675, font(19, True), ink)
        centered(draw, f"Confusions brut/net : {metrics['gross_net_confusions']}", x, 715, font(17), red)

    draw.line((115, 625, 1485, 625), fill=ink, width=2)
    draw.rounded_rectangle((125, 790, 1475, 985), radius=8, fill="#eff6ff")
    centered(draw, "Vérification du jeu de données", 800, 815, font(23, True), blue)
    centered(
        draw,
        f"{checks['distinct_customers']} clients × {checks['distinct_periods']} mois = {checks['gross_rows']} observations par mesure",
        800, 865, font(19), ink,
    )
    centered(
        draw,
        f"Net toujours inférieur au brut · corrélation = {checks['gross_net_correlation']:.6f}",
        800, 910, font(19), ink,
    )
    centered(draw, "A3 automatise la distinction ; A0 et A2 la définissent à l’avance ; A1 demande une validation.", 800, 950, font(17), muted)

    output = RESULTS / "s03_architecture_comparison.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    run()
