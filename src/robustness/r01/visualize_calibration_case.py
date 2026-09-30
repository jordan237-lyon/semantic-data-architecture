"""Visualize the isolated R01 S05/I1/seed-11 calibration run."""

import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.robustness.r01.paths import IMAGES_ROOT, RESULTS_ROOT


CASE = RESULTS_ROOT / "calibration_runs/S05/I1/seed-11"
PLOTS = CASE / "plots"
IMAGE_DESTINATION = IMAGES_ROOT / "calibration_runs/S05/I1/seed-11"


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def centered(draw, text, x, y, selected_font, fill="#172033"):
    width = draw.textbbox((0, 0), text, font=selected_font)[2]
    draw.text((x - width / 2, y), text, font=selected_font, fill=fill)


def quality_plot(summary):
    architectures = summary["architectures"]
    image = Image.new("RGB", (1700, 1050), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red, blue = "#16a34a", "#f59e0b", "#dc2626", "#2563eb"
    centered(draw, "R01 · S05 / I1 / seed 11", 850, 35, font(42, True))
    centered(draw, "50 % tickets · 50 % clients · colonne customer_id", 850, 95, font(22), muted)
    entries = [
        ("A0", 1.0, 0, "3 règles manuelles", green),
        ("A1", architectures["A1"]["value_quality"]["f1_score"], 50, "mapping technique", red),
        ("A2 avant", architectures["A2"]["before_adaptation"]["value_quality"]["f1_score"], 50, "mapping statique", red),
        ("A2 après", architectures["A2"]["after_adaptation"]["value_quality"]["f1_score"], 0, "3 adaptations", green),
        ("A3", None, 0, "1 revue humaine", orange),
    ]
    baseline = 690
    draw.line((100, baseline, 1600, baseline), fill=ink, width=2)
    for index, (label, f1, errors, detail, color) in enumerate(entries):
        x = 220 + index * 315
        if f1 is None:
            height, value = 300, "REVUE"
        else:
            height, value = int(f1 * 430), f"F1 {f1:.2f}"
        draw.rectangle((x - 82, baseline - height, x + 82, baseline), fill=color)
        centered(draw, value, x, baseline - height / 2 - 12, font(21, True), "white")
        centered(draw, label, x, 720, font(21, True), ink)
        centered(draw, f"{errors} erreurs silencieuses", x, 765, font(16), red if errors else green)
        centered(draw, detail, x, 802, font(16), muted)
    draw.rounded_rectangle((150, 875, 1550, 990), radius=10, fill="#eff6ff")
    centered(draw, "A3 refuse une acceptation pourtant notée 1,0 car la marge entre candidats n'est que de 0,009.", 850, 900, font(20, True), blue)
    centered(draw, "La politique de confiance transforme une erreur potentielle en décision révisable.", 850, 947, font(18), ink)
    return image


def tradeoff_plot(summary):
    architectures = summary["architectures"]
    image = Image.new("RGB", (1700, 980), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    green, orange, red, blue, pale = "#16a34a", "#f59e0b", "#dc2626", "#2563eb", "#eff6ff"
    centered(draw, "R01 — Sécurité, effort et automatisation", 850, 35, font(40, True))
    centered(draw, "Lecture complémentaire du cas de calibration S05/I1", 850, 92, font(21), muted)
    headings = ["Approche", "Décision initiale", "Sûre ?", "Erreurs silencieuses", "Intervention"]
    xs = [230, 590, 900, 1210, 1500]
    for x, heading in zip(xs, headings):
        centered(draw, heading, x, 175, font(18, True), ink)
    draw.line((90, 220, 1610, 220), fill=ink, width=2)
    rows = [
        ("A0 · manuel", "séparation", True, 0, "3 règles"),
        ("A1 · technique", "accepté", False, 50, "aucune"),
        ("A2 · déclaratif", "accepté", False, 50, "3 adaptations"),
        ("A3 · adaptatif", "revue", True, 0, "1 validation"),
    ]
    for index, (label, decision, safe, errors, effort) in enumerate(rows):
        y = 275 + index * 135
        if index % 2 == 0:
            draw.rounded_rectangle((90, y - 25, 1610, y + 75), radius=8, fill=pale)
        draw.text((125, y), label, font=font(20, True), fill=ink)
        centered(draw, decision, xs[1], y, font(19), orange if decision == "revue" else blue)
        centered(draw, "Oui" if safe else "Non", xs[2], y, font(19, True), green if safe else red)
        centered(draw, str(errors), xs[3], y, font(20, True), red if errors else green)
        centered(draw, effort, xs[4], y, font(18), ink)
    draw.rounded_rectangle((170, 820, 1530, 920), radius=10, fill="#ecfdf3")
    centered(draw, "Sécurité initiale : A0 et A3 · Automatisation correcte sans adaptation : aucune sur ce cas ambigu", 850, 850, font(19, True), green)
    centered(draw, "Les temps d'exécution restent descriptifs à cette échelle.", 850, 890, font(16), muted)
    return image


def save_both(image, filename):
    PLOTS.mkdir(parents=True, exist_ok=True)
    IMAGE_DESTINATION.mkdir(parents=True, exist_ok=True)
    result_path = PLOTS / filename
    image.save(result_path)
    image_path = IMAGE_DESTINATION / filename
    shutil.copy2(result_path, image_path)
    return result_path, image_path


def run():
    summary = json.loads((CASE / "summary.json").read_text(encoding="utf-8"))
    outputs = []
    outputs.extend(save_both(quality_plot(summary), "r01_s05_i1_quality.png"))
    outputs.extend(save_both(tradeoff_plot(summary), "r01_s05_i1_tradeoffs.png"))
    for output in outputs:
        print(output)
    return outputs


if __name__ == "__main__":
    run()
