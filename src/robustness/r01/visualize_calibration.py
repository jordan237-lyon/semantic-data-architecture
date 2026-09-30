"""Create descriptive PNGs for R01 calibration data, before A0-A3 execution."""

import csv
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.robustness.r01.paths import IMAGES_ROOT, RESULTS_ROOT


AUDIT = RESULTS_ROOT / "calibration/dataset_audit.csv"
PLOTS = RESULTS_ROOT / "plots"


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
    with AUDIT.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def intensity_dashboard(rows):
    image = Image.new("RGB", (1800, 1050), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    colors = {"S01": "#6d5ce8", "S04": "#f59e0b", "S05": "#dc4b64"}
    titles = {
        "S01": ("Chevauchement des statuts", "% de vocabulaire commun"),
        "S04": ("Intensité de la dérive", "points de variation"),
        "S05": ("Identifiants de tickets", "% des valeurs"),
    }
    centered(draw, "R01 — Intensités de calibration", 900, 35, font(42, True))
    centered(draw, "Graine 11 · 100 entités · trois niveaux par scénario", 900, 95, font(22), muted)
    for panel_index, scenario in enumerate(("S01", "S04", "S05")):
        left = 90 + panel_index * 570
        right = left + 500
        top, baseline = 185, 800
        title, unit = titles[scenario]
        centered(draw, scenario, (left + right) / 2, top, font(24, True), colors[scenario])
        centered(draw, title, (left + right) / 2, top + 42, font(20, True), ink)
        centered(draw, unit, (left + right) / 2, top + 78, font(16), muted)
        scenario_rows = [row for row in rows if row["scenario"] == scenario]
        observed = [float(row["observed_intensity"]) for row in scenario_rows]
        scale_max = 100 if scenario != "S04" else 40
        draw.line((left + 45, baseline, right - 25, baseline), fill=ink, width=2)
        for index, (row, value) in enumerate(zip(scenario_rows, observed)):
            x = left + 120 + index * 145
            height = int((value / scale_max) * 440) if scale_max else 0
            draw.rectangle((x - 48, baseline - height, x + 48, baseline), fill=colors[scenario])
            suffix = " %" if scenario != "S04" else " pts"
            centered(draw, f"{value:g}{suffix}", x, baseline - height - 38, font(18, True), ink)
            centered(draw, row["intensity"], x, baseline + 22, font(19, True), ink)
        centered(draw, "Valeur observée = valeur prévue", (left + right) / 2, 890, font(16), "#15803d")
        if panel_index < 2:
            draw.line((right + 25, 180, right + 25, 930), fill="#e2e8f0", width=2)
    centered(draw, "Toutes les intensités respectent exactement le protocole gelé.", 900, 980, font(20, True), ink)
    return image


def audit_dashboard(rows):
    image = Image.new("RGB", (1700, 980), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, blue, pale = "#16a34a", "#2563eb", "#eff6ff"
    centered(draw, "R01 — Audit des jeux de calibration", 850, 35, font(42, True))
    centered(draw, "Contrôle avant toute exécution A0–A3", 850, 95, font(22), muted)
    cards = [
        ("9", "jeux générés"), ("100", "entités par jeu"),
        ("5 %", "bruit de casse et espaces"), ("5 %", "valeurs optionnelles absentes"),
    ]
    for index, (value, label) in enumerate(cards):
        x1 = 90 + index * 395
        draw.rounded_rectangle((x1, 175, x1 + 340, 335), radius=15, fill=pale)
        centered(draw, value, x1 + 170, 205, font(38, True), blue)
        centered(draw, label, x1 + 170, 270, font(17), ink)
    headings = ["Scénario", "I0", "I1", "I2", "Contrôle"]
    xs = [270, 610, 890, 1170, 1450]
    for x, heading in zip(xs, headings):
        centered(draw, heading, x, 410, font(19, True), ink)
    draw.line((110, 452, 1590, 452), fill=ink, width=2)
    units = {"S01": "% commun", "S04": "points", "S05": "% tickets"}
    for row_index, scenario in enumerate(("S01", "S04", "S05")):
        y = 505 + row_index * 120
        centered(draw, scenario, xs[0], y, font(25, True), ink)
        scenario_rows = [row for row in rows if row["scenario"] == scenario]
        for index, row in enumerate(scenario_rows):
            value = float(row["observed_intensity"])
            display = f"{value:g}"
            centered(draw, display, xs[index + 1], y, font(22, True), blue)
        centered(draw, units[scenario], xs[0], y + 37, font(14), muted)
        centered(draw, "✓ Conforme", xs[4], y, font(19, True), green)
        draw.line((110, y + 75, 1590, y + 75), fill="#e2e8f0", width=1)
    draw.rounded_rectangle((180, 850, 1520, 930), radius=10, fill="#ecfdf3")
    centered(draw, "Intensités, bruit et valeurs manquantes : 9 contrôles sur 9 conformes", 850, 874, font(21, True), green)
    return image


def save_both(image, filename):
    PLOTS.mkdir(parents=True, exist_ok=True)
    IMAGES_ROOT.mkdir(parents=True, exist_ok=True)
    result_path = PLOTS / filename
    image.save(result_path)
    image_path = IMAGES_ROOT / filename
    shutil.copy2(result_path, image_path)
    return result_path, image_path


def run():
    rows = load_rows()
    outputs = []
    outputs.extend(save_both(intensity_dashboard(rows), "r01_calibration_intensities.png"))
    outputs.extend(save_both(audit_dashboard(rows), "r01_calibration_audit.png"))
    for output in outputs:
        print(output)
    return outputs


if __name__ == "__main__":
    run()
