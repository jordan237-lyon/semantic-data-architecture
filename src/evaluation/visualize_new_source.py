"""Generate a PNG dashboard for the fourth-source experiment."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "new_source" / "loyalty" / "before_adaptation"


def _font(size, bold=False):
    filename = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(
            str(Path("/System/Library/Fonts/Supplemental") / filename), size
        )
    except OSError:
        return ImageFont.load_default()


def run():
    result = json.loads((RESULTS / "results.json").read_text(encoding="utf-8"))
    analysis = result["semantic"]["standalone_schema_analysis"]
    image = Image.new("RGB", (1500, 930), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"

    def centered(text, y, font, fill=ink):
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((1500 - box[2]) / 2, y), text, font=font, fill=fill)

    centered("Ajout d’une quatrième source — état initial", 35, _font(38, True))
    centered("loyalty.csv · 80 membres · 5 colonnes inconnues", 92, _font(21), muted)
    draw.rounded_rectangle((90, 170, 680, 410), radius=10, fill="#fee2e2")
    draw.rounded_rectangle((820, 170, 1410, 410), radius=10, fill="#fee2e2")
    centered_x = lambda text, x, y, font, fill=ink: draw.text(
        (x - draw.textbbox((0, 0), text, font=font)[2] / 2, y),
        text, font=font, fill=fill,
    )
    centered_x("Baseline", 385, 205, _font(28, True))
    centered_x("Sémantique", 1115, 205, _font(28, True))
    centered_x("0 %", 385, 265, _font(52, True), "#dc2626")
    centered_x("0 %", 1115, 265, _font(52, True), "#dc2626")
    centered_x("couverture loyalty", 385, 335, _font(21), muted)
    centered_x("couverture loyalty", 1115, 335, _font(21), muted)
    centered_x("liste de sources codée en dur", 385, 375, _font(19), muted)
    centered_x("orchestration également codée en dur", 1115, 375, _font(19), muted)

    centered("Capacité du matcher sémantique pris isolément", 490, _font(29, True))
    labels = [
        ("Colonnes analysées", analysis["columns_profiled"], "#2563eb"),
        ("Meilleurs candidats corrects", analysis["correct_best_candidates"], "#16a34a"),
        ("Accepté automatiquement", analysis["accepted"], "#2563eb"),
        ("À valider", analysis["review"], "#f59e0b"),
        ("Rejeté", analysis["rejected"], "#dc2626"),
    ]
    x = 130
    for label, value, color in labels:
        draw.rounded_rectangle((x, 565, x + 230, 730), radius=8, fill="#f8fafc", outline="#d8dee9")
        centered_x(str(value), x + 115, 590, _font(42, True), color)
        words = label.split()
        if len(words) > 2:
            centered_x(" ".join(words[:2]), x + 115, 665, _font(17), muted)
            centered_x(" ".join(words[2:]), x + 115, 691, _font(17), muted)
        else:
            centered_x(label, x + 115, 677, _font(17), muted)
        x += 270
    centered("Conclusion : la compréhension partielle existe, mais la découverte automatique manque encore.", 815, _font(22, True))
    centered("Prochaine adaptation : découverte des CSV + validation des mappings loyalty.", 860, _font(20), muted)
    plots = RESULTS / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    path = plots / "new_source_before_adaptation.png"
    image.save(path)
    print(path)


if __name__ == "__main__":
    run()
