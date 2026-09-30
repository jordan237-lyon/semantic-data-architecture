"""Generate explanatory PNG visuals for A1 on P00."""

import csv
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "benchmark_v2" / "P00" / "A1"
PLOTS = RESULTS / "plots"


def _font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(
            str(Path("/System/Library/Fonts/Supplemental") / name), size
        )
    except OSError:
        return ImageFont.load_default()


def _center(draw, text, x, y, font, fill="#172033"):
    width = draw.textbbox((0, 0), text, font=font)[2]
    draw.text((x - width / 2, y), text, font=font, fill=fill)


def _load():
    metrics = json.loads((RESULTS / "metrics.json").read_text(encoding="utf-8"))
    with (RESULTS / "technical_mappings.csv").open(newline="", encoding="utf-8") as stream:
        mappings = list(csv.DictReader(stream))
    return metrics, mappings


def dashboard(metrics, mappings):
    image = Image.new("RGB", (1500, 980), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, blue, green, orange = "#172033", "#667085", "#2563eb", "#16a34a", "#f59e0b"
    _center(draw, "A1 / P00 — découverte et métadonnées techniques", 750, 35, _font(38, True))
    _center(draw, "Sans modèle métier, sans synonymes et sans relations YAML", 750, 92, _font(21), muted)

    cards = [
        ("Sources découvertes", str(len(metrics["discovered_sources"])), blue),
        ("Colonnes profilées", str(metrics["profiled_columns"]), blue),
        ("Rôles attribués", str(metrics["mapped_technical_roles"]), green),
        ("À revoir", str(metrics["review_columns"]), orange),
    ]
    for index, (label, value, color) in enumerate(cards):
        left = 85 + index * 355
        draw.rounded_rectangle((left, 155, left + 300, 330), radius=10, fill="#f8fafc", outline="#d8dee9")
        _center(draw, value, left + 150, 190, _font(45, True), color)
        _center(draw, label, left + 150, 265, _font(19), muted)

    _center(draw, "Pipeline technique observé", 750, 390, _font(29, True))
    steps = [
        ("Découverte", "3 CSV"),
        ("Profilage", "types + formats"),
        ("Inférence", "e-mail + identifiant"),
        ("Fusion", "clé e-mail"),
        ("Évaluation", "251 liens corrects"),
    ]
    for index, (title, subtitle) in enumerate(steps):
        left = 55 + index * 290
        draw.rounded_rectangle((left, 455, left + 240, 585), radius=8, fill="#dbeafe")
        _center(draw, title, left + 120, 482, _font(21, True))
        _center(draw, subtitle, left + 120, 530, _font(17), muted)
        if index < len(steps) - 1:
            draw.line((left + 245, 520, left + 278, 520), fill=blue, width=4)
            draw.polygon([(left + 278, 520), (left + 265, 512), (left + 265, 528)], fill=blue)

    quality = metrics["entity_quality"]
    _center(draw, "Qualité du matching d’entités", 750, 650, _font(29, True))
    values = [
        ("Precision", quality["precision"], green),
        ("Recall", quality["recall"], blue),
        ("F1", quality["f1_score"], orange),
    ]
    for index, (label, value, color) in enumerate(values):
        x = 350 + index * 400
        _center(draw, f"{value:.3f}", x, 710, _font(44, True), color)
        _center(draw, label, x, 770, _font(19), muted)

    draw.rounded_rectangle((125, 835, 1375, 930), radius=9, fill="#fef3c7")
    _center(draw, "Lecture correcte", 750, 852, _font(21, True))
    _center(draw, "A1 sait relier les entités grâce aux formats, mais 6 textes restent sans sens métier.", 750, 890, _font(20), ink)
    image.save(PLOTS / "a1_p00_dashboard.png")


def column_map(mappings):
    image = Image.new("RGB", (1700, 1160), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    role_colors = {
        "identifier": "#2563eb", "email": "#16a34a", "date": "#8b5cf6",
        "country_code": "#0d9488", "numeric_measure": "#f59e0b",
        "unclassified_text": "#dc2626",
    }
    _center(draw, "A1 / P00 — lecture technique des 19 colonnes", 850, 35, _font(38, True))
    _center(draw, "Rouge : information textuelle non interprétable sans connaissance métier", 850, 92, _font(21), muted)
    sources = ["crm", "finance", "support"]
    x_positions = {"crm": 100, "finance": 625, "support": 1150}
    for source in sources:
        left = x_positions[source]
        selected = [row for row in mappings if row["source"] == source]
        _center(draw, source.upper(), left + 225, 155, _font(27, True))
        y = 215
        for row in selected:
            color = role_colors[row["technical_role"]]
            draw.rounded_rectangle((left, y, left + 450, y + 85), radius=7, fill="#f8fafc", outline="#d8dee9")
            draw.rectangle((left, y, left + 12, y + 85), fill=color)
            draw.text((left + 32, y + 14), row["source_column"], font=_font(20, True), fill=ink)
            draw.text((left + 32, y + 48), row["technical_role"], font=_font(17), fill=color)
            draw.text((left + 355, y + 31), f"{float(row['confidence']):.2f}", font=_font(18, True), fill=ink)
            y += 105
    counts = Counter(row["technical_role"] for row in mappings)
    legend = " · ".join(f"{role}: {count}" for role, count in counts.items())
    _center(draw, legend, 850, 1085, _font(18), muted)
    image.save(PLOTS / "a1_p00_column_roles.png")


def run():
    metrics, mappings = _load()
    PLOTS.mkdir(parents=True, exist_ok=True)
    dashboard(metrics, mappings)
    column_map(mappings)
    print(PLOTS / "a1_p00_dashboard.png")
    print(PLOTS / "a1_p00_column_roles.png")


if __name__ == "__main__":
    run()
