"""Generate the S02 semantic-equivalence comparison as PNG."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2/S02"


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
    centered(draw, "S02 — noms différents, même sens", 800, 35, font(40, True))
    centered(draw, "Mapping des deux montants au niveau transactionnel", 800, 92, font(22), muted)

    architectures = ["A0", "A1", "A2", "A3"]
    subtitles = ["Manuel", "Technique", "Déclaratif", "Adaptatif"]
    for index, architecture in enumerate(architectures):
        metrics = summary[architecture]["schema_quality"]
        x = 235 + index * 380
        accepted, review = metrics["accepted_correct"], metrics["review_mappings"]
        centered(draw, architecture, x, 180, font(28, True), ink)
        centered(draw, subtitles[index], x, 220, font(17), muted)
        color = green if accepted else orange
        value = accepted if accepted else review
        draw.rectangle((x - 90, 300, x + 90, 630), fill=color)
        centered(draw, f"{value} corrects" if accepted else f"{value} en revue", x, 445, font(21, True), "white")
        centered(draw, f"Couverture : {metrics['coverage'] * 100:.0f} %", x, 680, font(19, True), ink)
        centered(draw, f"Confusions revenue : {metrics['accepted_as_customer_revenue']}", x, 720, font(17), red)

    draw.line((115, 630, 1485, 630), fill=ink, width=2)
    draw.rounded_rectangle((125, 790, 1475, 925), radius=8, fill="#eff6ff")
    centered(draw, "gross_amount = turnover_value = Transaction.amount", 800, 810, font(25, True), blue)
    centered(draw, "A0, A2 et A3 : 2/2 mappings corrects · A1 : 2 revues · aucun mapping vers Customer.revenue", 800, 860, font(19), ink)
    output = RESULTS / "s02_architecture_comparison.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    run()
