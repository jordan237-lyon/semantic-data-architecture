"""Generate the before/after PNG for the fourth-source integration."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "results" / "new_source" / "loyalty"


def _font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def run():
    after = json.loads((BASE / "after_adaptation" / "results.json").read_text(encoding="utf-8"))
    image = Image.new("RGB", (1500, 980), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"

    def center(text, x, y, font, fill=ink):
        width = draw.textbbox((0, 0), text, font=font)[2]
        draw.text((x - width / 2, y), text, font=font, fill=fill)

    center("Quatrième source Loyalty — avant et après adaptation", 750, 38, _font(38, True))
    center("80 membres à intégrer", 750, 95, _font(21), muted)
    center("Baseline", 390, 170, _font(30, True))
    center("Sémantique", 1110, 170, _font(30, True))
    for x, key in ((390, "baseline"), (1110, "semantic")):
        draw.rounded_rectangle((x - 280, 225, x + 280, 470), radius=10, fill="#f8fafc", outline="#d8dee9")
        center("0 %", x - 125, 270, _font(44, True), "#dc2626")
        center("→", x, 278, _font(34, True), muted)
        center("100 %", x + 135, 270, _font(44, True), "#16a34a")
        center("couverture avant / après", x, 335, _font(19), muted)
        quality = after[key]["loyalty_quality"]
        center(f"Precision {quality['precision']:.3f} · Recall {quality['recall']:.3f}", x, 390, _font(20, True))
        center(f"F1 {quality['f1_score']:.3f}", x, 430, _font(22, True), "#16a34a")
    center("Effort d’intégration", 750, 540, _font(29, True))
    draw.rounded_rectangle((120, 600, 690, 825), radius=10, fill="#fee2e2")
    draw.rounded_rectangle((810, 600, 1380, 825), radius=10, fill="#dbeafe")
    center("5 mappings manuels", 405, 645, _font(25, True))
    center("5 règles manuelles", 405, 700, _font(25, True))
    center("2 fichiers Python", 405, 755, _font(22), muted)
    center("4 synonymes YAML", 1095, 645, _font(25, True))
    center("5 mappings automatiques", 1095, 700, _font(25, True))
    center("0 validation humaine", 1095, 755, _font(22), muted)
    center("Les deux atteignent 100 % ; la sémantique automatise les mappings après enrichissement du vocabulaire.", 750, 890, _font(21, True))
    plots = BASE / "after_adaptation" / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    path = plots / "new_source_before_after.png"
    image.save(path)
    print(path)


if __name__ == "__main__":
    run()
