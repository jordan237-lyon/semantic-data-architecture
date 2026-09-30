"""Generate an SVG dashboard for the scale experiment."""

import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "scale"


def _rows(path=None):
    path = path or RESULTS / "scale_summary.csv"
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _points(rows, metric, x0, y0, width, height, maximum):
    xs = {1: x0, 5: x0 + width / 2, 10: x0 + width}
    return [
        (xs[int(row["scale_factor"])], y0 + height - float(row[metric]) / maximum * height)
        for row in rows
    ]


def _line(points, color):
    path = " ".join(f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}" for index, (x, y) in enumerate(points))
    content = [f'<path d="{path}" fill="none" stroke="{color}" stroke-width="4"/>']
    for x, y in points:
        content.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{color}"/>')
    return "".join(content)


def _font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    path = Path("/System/Library/Fonts/Supplemental") / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def png_dashboard(rows, before_rows, path):
    image = Image.new("RGB", (1600, 1120), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, blue, gray, grid = "#172033", "#667085", "#2563eb", "#64748b", "#d8dee9"

    def centered(text, y, font, fill=ink):
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(((1600 - box[2]) / 2, y), text, font=font, fill=fill)

    def plot(selected_metric, title, bounds, maximum, formatter):
        left, top, right, bottom = bounds
        draw.text((left, top - 55), title, font=_font(28, True), fill=ink)
        draw.rectangle(bounds, outline=grid, width=2)
        for tick in range(3):
            y = bottom - (bottom - top) * tick / 2
            draw.line((left, y, right, y), fill=grid, width=2)
            value = maximum * tick / 2
            draw.text((left - 75, y - 10), formatter(value), font=_font(17), fill=muted)
        xs = {1: left, 5: (left + right) / 2, 10: right}
        for factor, x in xs.items():
            draw.text((x - 12, bottom + 15), f"{factor}×", font=_font(18), fill=muted)
        for pipeline, color in (("baseline", gray), ("semantic", blue)):
            selected = [row for row in rows if row["pipeline"] == pipeline]
            points = []
            for row in selected:
                value = float(row[selected_metric])
                x = xs[int(row["scale_factor"])]
                y = bottom - value / maximum * (bottom - top)
                points.append((x, y, value))
            draw.line([(x, y) for x, y, _ in points], fill=color, width=6)
            for x, y, value in points:
                draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=color)
                draw.text((x - 25, y - 34), formatter(value), font=_font(16, True), fill=ink)
        if selected_metric == "f1_score":
            selected = [row for row in before_rows if row["pipeline"] == "baseline"]
            points = []
            for row in selected:
                value = float(row[selected_metric])
                x = xs[int(row["scale_factor"])]
                y = bottom - value / maximum * (bottom - top)
                points.append((x, y))
            draw.line(points, fill="#dc2626", width=4)
            for x, y in points:
                draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill="#dc2626")

    centered("Passage à l’échelle — performance et robustesse", 30, _font(38, True))
    centered("865 → 4 325 → 8 650 lignes sources · médianes sur 5 exécutions", 85, _font(20), muted)
    draw.line((580, 135, 640, 135), fill=gray, width=6)
    draw.text((655, 122), "Baseline", font=_font(20), fill=muted)
    draw.line((815, 135, 875, 135), fill=blue, width=6)
    draw.text((890, 122), "Sémantique", font=_font(20), fill=muted)
    draw.line((1040, 135, 1100, 135), fill="#dc2626", width=4)
    draw.text((1115, 122), "Baseline avant correction", font=_font(20), fill=muted)
    plot("median_wall_time_seconds", "Temps médian (s)", (140, 245, 730, 530), 0.5, lambda v: f"{v:.3f}")
    plot("memory_mb", "Pic mémoire Python (Mo)", (900, 245, 1490, 530), 4.0, lambda v: f"{v:.1f}")
    plot("f1_score", "Qualité du matching (F1)", (300, 720, 1300, 980), 1.0, lambda v: f"{v:.3f}")
    centered("À 10× : baseline 0,833 → 0,979 après correction des e-mails absents", 1050, _font(23, True))
    image.save(path)


def chart(rows, metric, title, unit, x0, y0, width, height, maximum, decimals=3):
    baseline = [row for row in rows if row["pipeline"] == "baseline"]
    semantic = [row for row in rows if row["pipeline"] == "semantic"]
    parts = [
        f'<text x="{x0 + width / 2}" y="{y0 - 35}" text-anchor="middle" class="head">{title}</text>',
        f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" fill="none" stroke="#d8dee9"/>',
    ]
    for tick in range(3):
        value = maximum * tick / 2
        y = y0 + height - height * tick / 2
        parts.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + width}" y2="{y}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{x0 - 10}" y="{y + 4}" text-anchor="end" class="small">{value:.{decimals}f}</text>')
    for factor, x in ((1, x0), (5, x0 + width / 2), (10, x0 + width)):
        parts.append(f'<text x="{x}" y="{y0 + height + 25}" text-anchor="middle" class="small">{factor}×</text>')
    for selected, color in ((baseline, "#64748b"), (semantic, "#2563eb")):
        points = _points(selected, metric, x0, y0, width, height, maximum)
        parts.append(_line(points, color))
        for row, (x, y) in zip(selected, points):
            value = float(row[metric])
            parts.append(f'<text x="{x}" y="{y - 11}" text-anchor="middle" class="value">{value:.{decimals}f}</text>')
    parts.append(f'<text x="{x0 + width / 2}" y="{y0 + height + 48}" text-anchor="middle" class="small">Taille du dataset · {unit}</text>')
    return "".join(parts)


def run():
    rows = _rows()
    before_rows = _rows(RESULTS / "before_null_fix" / "scale_summary.csv")
    for row in rows:
        row["memory_mb"] = str(int(row["median_python_peak_memory_bytes"]) / 1_000_000)
    body = [
        '<text x="575" y="42" text-anchor="middle" class="title">Passage à l’échelle — performance et robustesse</text>',
        '<text x="575" y="70" text-anchor="middle" class="sub">865 → 4 325 → 8 650 lignes sources · médianes sur 5 exécutions</text>',
        '<line x1="420" y1="100" x2="455" y2="100" stroke="#64748b" stroke-width="4"/><text x="465" y="105" class="small">Baseline</text>',
        '<line x1="600" y1="100" x2="635" y2="100" stroke="#2563eb" stroke-width="4"/><text x="645" y="105" class="small">Sémantique</text>',
        '<line x1="755" y1="100" x2="790" y2="100" stroke="#dc2626" stroke-width="3"/><text x="800" y="105" class="small">Baseline avant correction</text>',
        chart(rows, "median_wall_time_seconds", "Temps médian", "secondes", 90, 175, 430, 190, 0.50, 3),
        chart(rows, "memory_mb", "Pic mémoire Python", "Mo", 650, 175, 410, 190, 4.0, 1),
        chart(rows, "f1_score", "Qualité du matching", "score F1", 200, 510, 750, 170, 1.0, 3),
        _line(_points(
            [row for row in before_rows if row["pipeline"] == "baseline"],
            "f1_score", 200, 510, 750, 170, 1.0
        ), "#dc2626"),
        '<text x="575" y="765" text-anchor="middle" class="note">À 10× : baseline 0,833 → 0,979 après correction des e-mails absents.</text>',
    ]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1150" height="800" viewBox="0 0 1150 800" role="img" aria-labelledby="t d"><title id="t">Passage à l’échelle</title><desc id="d">Comparaison du temps, de la mémoire et du F1 pour les tailles 1, 5 et 10.</desc><rect width="1150" height="800" fill="white"/><style>text{{font-family:Arial,sans-serif;fill:#172033}}.title{{font-size:25px;font-weight:700}}.sub,.small{{font-size:12px;fill:#667085}}.head{{font-size:18px;font-weight:700}}.value{{font-size:11px;font-weight:700}}.note{{font-size:14px;font-weight:700}}</style>{''.join(body)}</svg>'''
    plots = RESULTS / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    path = plots / "scale_dashboard.svg"
    path.write_text(svg, encoding="utf-8")
    png_dashboard(rows, before_rows, plots / "scale_dashboard.png")
    print(path)
    print(plots / "scale_dashboard.png")


if __name__ == "__main__":
    run()
