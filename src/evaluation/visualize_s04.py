"""Generate the S04 temporal semantic-drift comparison as PNG."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2/S04"


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
    stats, architectures = payload["window_statistics"], payload["architectures"]
    image = Image.new("RGB", (1600, 1080), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red, blue, pale = "#16a34a", "#f59e0b", "#dc2626", "#2563eb", "#eff6ff"

    centered(draw, "S04 — dérive sémantique temporelle", 800, 35, font(40, True))
    centered(draw, "Même colonne active · même type booléen · définition différente", 800, 92, font(22), muted)

    baseline_y = 430
    draw.line((170, baseline_y, 760, baseline_y), fill=ink, width=2)
    for x, label, rate, color in (
        (330, "Avant rupture", stats["before_true_rate"], blue),
        (600, "Après rupture", stats["after_true_rate"], orange),
    ):
        height = int(rate * 260)
        draw.rectangle((x - 75, baseline_y - height, x + 75, baseline_y), fill=color)
        centered(draw, f"{rate * 100:.0f} %", x, baseline_y - height - 45, font(25, True), ink)
        centered(draw, label, x, baseline_y + 25, font(18), ink)
    centered(draw, "Taux de valeurs true", 465, 510, font(17), muted)
    centered(draw, "Rupture mesurée : 15 points", 465, 550, font(22, True), red)

    draw.rounded_rectangle((860, 155, 1450, 570), radius=10, fill=pale)
    centered(draw, "Changement de sens", 1155, 185, font(25, True), blue)
    centered(draw, "jusqu’au 30/06/2025", 1155, 250, font(17), muted)
    centered(draw, "activité dans les 90 jours", 1155, 285, font(22, True), ink)
    draw.line((980, 355, 1330, 355), fill=red, width=4)
    centered(draw, "01/07/2025", 1155, 370, font(18, True), red)
    centered(draw, "à partir du 01/07/2025", 1155, 435, font(17), muted)
    centered(draw, "contrat payant en cours", 1155, 470, font(22, True), ink)

    headings = ["Architecture", "Détection", "Revue", "Erreur silencieuse", "Adaptation"]
    xs = [235, 560, 800, 1080, 1390]
    for x, heading in zip(xs, headings):
        centered(draw, heading, x, 660, font(18, True), ink)
    draw.line((100, 700, 1500, 700), fill=ink, width=2)

    rows = [
        ("A0 · manuel", architectures["A0"], "0", "2 règles"),
        ("A1 · métadonnées", architectures["A1"], "1", "0"),
        ("A2 · avant", architectures["A2"]["before_adaptation"], "0", "0"),
        ("A2 · après", architectures["A2"]["after_adaptation"], "0", "1 version"),
        ("A3 · adaptatif", architectures["A3"], "1", "0"),
    ]
    for index, (label, result, reviews, adaptation) in enumerate(rows):
        y = 735 + index * 62
        draw.text((125, y), label, font=font(18, True), fill=ink)
        centered(draw, "Oui" if result["drift_detected"] else "Non", xs[1], y, font(18, True), green if result["drift_detected"] else red)
        centered(draw, reviews, xs[2], y, font(18), ink)
        silent = result["silent_wrong_acceptances"]
        centered(draw, str(silent), xs[3], y, font(18, True), red if silent else green)
        centered(draw, adaptation, xs[4], y, font(18), ink)

    output = RESULTS / "s04_drift_comparison.png"
    image.save(output)
    print(output)


if __name__ == "__main__":
    run()
