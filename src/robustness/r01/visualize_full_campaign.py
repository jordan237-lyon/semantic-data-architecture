"""Create PNG summaries for the completed R01 campaign."""

import csv
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.robustness.r01.paths import IMAGES_ROOT, RESULTS_ROOT


PLOTS = RESULTS_ROOT / "plots" / "full_campaign"
IMAGES = IMAGES_ROOT / "full_campaign"
COLORS = {"A0": "#2563eb", "A1": "#0891b2", "A2": "#f59e0b", "A3": "#16a34a"}
INK, MUTED, RED = "#172033", "#667085", "#dc2626"


def font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def center(draw, text, x, y, selected_font, fill=INK):
    bounds = draw.textbbox((0, 0), text, font=selected_font)
    draw.text((x - (bounds[2] - bounds[0]) / 2, y), text, font=selected_font, fill=fill)


def read_csv(path):
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def dashboard(architectures):
    image = Image.new("RGB", (1800, 1120), "white")
    draw = ImageDraw.Draw(image)
    center(draw, "R01 — Résultats des 72 exécutions de test", 900, 35, font(42, True))
    center(draw, "Graines 22 et 33 · calibration seed 11 exclue des agrégats", 900, 92, font(21), MUTED)
    baseline = 610
    draw.line((100, baseline, 1700, baseline), fill=INK, width=2)
    for index, row in enumerate(architectures):
        name = row["architecture"]
        x = 280 + index * 420
        initial, final = float(row["initial_score_mean"]), float(row["final_score_mean"])
        initial_height, final_height = int(initial * 380), int(final * 380)
        draw.rectangle((x - 105, baseline - initial_height, x - 10, baseline), fill="#cbd5e1")
        draw.rectangle((x + 10, baseline - final_height, x + 105, baseline), fill=COLORS[name])
        center(draw, f"{initial:.2f}", x - 57, baseline - initial_height / 2 - 10, font(17, True), INK)
        center(draw, f"{final:.2f}", x + 57, baseline - final_height / 2 - 10, font(17, True), "white")
        center(draw, name, x, 640, font(24, True))
        center(draw, f"sûr au départ : {float(row['initial_safe_rate']):.0%}", x, 690, font(17), COLORS[name])
        silent = int(row["silent_wrong_acceptances_initial_total"])
        center(draw, f"{silent} erreurs silencieuses initiales", x, 730, font(16), RED if silent else COLORS[name])
    draw.rectangle((610, 805, 680, 835), fill="#cbd5e1")
    draw.text((700, 808), "score initial moyen", font=font(17), fill=INK)
    draw.rectangle((950, 805, 1020, 835), fill="#2563eb")
    draw.text((1040, 808), "score final moyen", font=font(17), fill=INK)
    draw.rounded_rectangle((150, 910, 1650, 1045), radius=12, fill="#eff6ff")
    center(draw, "A2 passe de 0,50 à 1,00 après adaptation, mais produit 306 erreurs silencieuses dans son état initial.", 900, 940, font(19, True), "#2563eb")
    center(draw, "A3 reste sûr dans 100 % des tests, avec 20 revues humaines et aucune erreur silencieuse.", 900, 990, font(18), INK)
    return image


def sensitivity(rows):
    image = Image.new("RGB", (1800, 1220), "white")
    draw = ImageDraw.Draw(image)
    center(draw, "R01 — Sensibilité à l'intensité", 900, 35, font(42, True))
    center(draw, "Score initial moyen sur les graines de test 22 et 33", 900, 92, font(21), MUTED)
    for index, architecture in enumerate(("A0", "A1", "A2", "A3")):
        x = 560 + index * 230
        draw.line((x - 55, 145, x - 10, 145), fill=COLORS[architecture], width=6)
        draw.text((x, 132), architecture, font=font(17, True), fill=COLORS[architecture])
    scenarios = [("S01", "Chevauchement des vocabulaires"), ("S04", "Dérive temporelle"), ("S05", "Identifiants de tickets")]
    intensities = ["I0", "I1", "I2"]
    for panel, (scenario, subtitle) in enumerate(scenarios):
        top = 190 + panel * 330
        draw.text((115, top), f"{scenario} · {subtitle}", font=font(23, True), fill=INK)
        left, right, chart_top, chart_bottom = 250, 1650, top + 55, top + 270
        draw.rectangle((left, chart_top, right, chart_bottom), outline="#d0d5dd", width=2)
        for value in (0.0, 0.5, 1.0):
            y = chart_bottom - value * (chart_bottom - chart_top)
            draw.line((left, y, right, y), fill="#e5e7eb", width=1)
            draw.text((170, y - 10), f"{value:.1f}", font=font(15), fill=MUTED)
        xs = [450, 950, 1450]
        for x, intensity in zip(xs, intensities):
            center(draw, intensity, x, chart_bottom + 18, font(16, True), INK)
        for architecture in ("A0", "A1", "A2", "A3"):
            points = []
            for x, intensity in zip(xs, intensities):
                row = next(item for item in rows if item["scenario"] == scenario and item["intensity"] == intensity and item["architecture"] == architecture)
                value = float(row["initial_mean"])
                points.append((x, chart_bottom - value * (chart_bottom - chart_top)))
            draw.line(points, fill=COLORS[architecture], width=5)
            for x, y in points:
                draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=COLORS[architecture])
    return image


def effort(architectures):
    image = Image.new("RGB", (1800, 980), "white")
    draw = ImageDraw.Draw(image)
    center(draw, "R01 — Coût de la sécurité et de l'adaptation", 900, 35, font(42, True))
    center(draw, "Totaux sur 18 exécutions de test par architecture", 900, 92, font(21), MUTED)
    headers = ["Architecture", "Configurations", "Adaptations", "Revues humaines", "Erreurs finales"]
    xs = [230, 610, 930, 1250, 1570]
    for x, heading in zip(xs, headers):
        center(draw, heading, x, 175, font(18, True))
    draw.line((80, 220, 1720, 220), fill=INK, width=2)
    for index, row in enumerate(architectures):
        y = 285 + index * 135
        if index % 2 == 0:
            draw.rounded_rectangle((80, y - 25, 1720, y + 75), radius=8, fill="#eff6ff")
        name = row["architecture"]
        center(draw, name, xs[0], y, font(22, True), COLORS[name])
        center(draw, row["configuration_actions_total"], xs[1], y, font(20), INK)
        center(draw, row["adaptation_actions_total"], xs[2], y, font(20), INK)
        center(draw, row["human_reviews_total"], xs[3], y, font(20), INK)
        final_errors = int(row["silent_wrong_acceptances_final_total"])
        center(draw, str(final_errors), xs[4], y, font(20, True), RED if final_errors else COLORS[name])
    draw.rounded_rectangle((170, 820, 1630, 915), radius=10, fill="#ecfdf3")
    center(draw, "A0 achète l'exactitude par configuration ; A2 par adaptation ; A3 par revue humaine.", 900, 850, font(20, True), "#16a34a")
    center(draw, "A1 conserve 302 erreurs silencieuses après traitement sur ce protocole.", 900, 890, font(17), RED)
    return image


def save(image, name):
    PLOTS.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    result = PLOTS / name
    image.save(result)
    destination = IMAGES / name
    shutil.copy2(result, destination)
    return result, destination


def run():
    architectures = read_csv(RESULTS_ROOT / "architecture_summary.csv")
    scenarios = read_csv(RESULTS_ROOT / "scenario_summary.csv")
    outputs = []
    outputs.extend(save(dashboard(architectures), "r01_full_campaign_dashboard.png"))
    outputs.extend(save(sensitivity(scenarios), "r01_intensity_sensitivity.png"))
    outputs.extend(save(effort(architectures), "r01_effort_safety.png"))
    for output in outputs:
        print(output)
    return outputs


if __name__ == "__main__":
    run()
