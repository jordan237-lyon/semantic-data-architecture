"""Generate the S01 schema-ambiguity comparison as PNG."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2/S01"


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
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))["architectures"]
    image = Image.new("RGB", (1600, 980), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red, blue = "#16a34a", "#f59e0b", "#dc2626", "#2563eb"
    centered(draw, "S01 — même nom, sens différent", 800, 35, font(40, True))
    centered(draw, "Traitement des deux colonnes status par architecture", 800, 92, font(22), muted)

    architectures = ["A0", "A1", "A2", "A3"]
    subtitles = ["Règles manuelles", "Métadonnées", "Déclaratif", "Adaptatif"]
    for index, architecture in enumerate(architectures):
        metrics = summary[architecture]["schema_quality"]
        x = 235 + index * 380
        accepted = metrics["accepted_correct"]
        review = metrics["review_mappings"]
        wrong = metrics["accepted_incorrect"]
        centered(draw, architecture, x, 185, font(28, True), ink)
        centered(draw, subtitles[index], x, 225, font(17), muted)
        y = 630
        unit_height = 165
        if accepted:
            draw.rectangle((x - 90, y - accepted * unit_height, x + 90, y), fill=green)
            centered(draw, f"{accepted} correct(s)", x, y - accepted * unit_height / 2 - 14, font(20, True), "white")
            y -= accepted * unit_height
        if review:
            draw.rectangle((x - 90, y - review * unit_height, x + 90, y), fill=orange)
            centered(draw, f"{review} en revue", x, y - review * unit_height / 2 - 14, font(20, True), "white")
            y -= review * unit_height
        if wrong:
            draw.rectangle((x - 90, y - wrong * unit_height, x + 90, y), fill=red)
        centered(draw, f"Couverture : {metrics['coverage'] * 100:.0f} %", x, 680, font(19, True), ink)
        centered(draw, f"Candidats corrects : {metrics['candidate_accuracy'] * 100:.0f} %", x, 718, font(17), blue)

    draw.line((115, 630, 1485, 630), fill=ink, width=2)
    draw.rounded_rectangle((130, 790, 1470, 915), radius=8, fill="#eff6ff")
    centered(draw, "A3 trouve les deux bonnes cibles, mais refuse de les accepter automatiquement", 800, 815, font(23, True), blue)
    centered(draw, "Marge de confiance insuffisante → 2 revues humaines, 0 faux mapping accepté", 800, 862, font(20), ink)
    output = RESULTS / "s01_architecture_comparison.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    run()
