"""Build an explicit, evidence-backed comparison of benchmark V1 and V2."""

import csv
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "benchmark_comparison"
PLOTS = OUTPUT / "plots"
IMAGES = ROOT / "images" / "benchmark_comparison"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_evidence():
    v1 = read_json(RESULTS / "benchmark_v1/final/global_summary.json")
    v2_a1 = read_json(RESULTS / "benchmark_v2/P00/A1/metrics.json")
    v2_a2 = read_json(RESULTS / "benchmark_v2/P00/A2/metrics.json")
    v2_semantic = read_json(
        RESULTS / "benchmark_v2/semantic_benchmark/benchmark_summary.json"
    )
    return v1, v2_a1, v2_a2, v2_semantic


def build_summary():
    v1, v2_a1, v2_a2, v2_semantic = load_evidence()
    architectures = {item["architecture"]: item for item in v2_semantic["architectures"]}
    return {
        "comparison_scope": {
            "benchmark_v1": {
                "architectures": ["baseline", "semantic"],
                "structural_scenarios": ["P00", "P01", "P02", "P03", "P04", "P05"],
                "semantic_scenarios": [],
            },
            "benchmark_v2": {
                "architectures": ["A0", "A1", "A2", "A3"],
                "structural_scenarios": ["P00", "P01", "P02", "P03", "P04", "P05"],
                "semantic_scenarios": v2_semantic["scope"],
            },
        },
        "directly_comparable_nominal_entity_quality": {
            "metric": "entity matching on P00",
            "benchmark_v1_baseline": v1["final_nominal_quality"]["baseline"],
            "benchmark_v1_semantic": v1["final_nominal_quality"]["semantic"],
            "benchmark_v2_A1": v2_a1["entity_quality"],
            "benchmark_v2_A2": v2_a2["entity_quality"],
            "finding": "All measured approaches have the same nominal entity F1; V2 adds architectural and semantic-disambiguation coverage rather than a nominal-quality gain.",
        },
        "v1_performance_context": v1["final_performance"],
        "v2_semantic_scenario_results": architectures,
        "comparison_limits": [
            "V1 entity F1 and V2 semantic outcome scores measure different tasks and are not merged.",
            "V2 A0 and A3 nominal P00 timings were not re-benchmarked in the same execution batch as A1 and A2.",
            "Execution-time values from separate campaigns are descriptive, not causal evidence.",
        ],
    }


def write_csv(summary):
    quality = summary["directly_comparable_nominal_entity_quality"]
    rows = []
    labels = [
        ("benchmark_v1", "baseline", "benchmark_v1_baseline"),
        ("benchmark_v1", "semantic", "benchmark_v1_semantic"),
        ("benchmark_v2", "A1", "benchmark_v2_A1"),
        ("benchmark_v2", "A2", "benchmark_v2_A2"),
    ]
    for campaign, architecture, key in labels:
        value = quality[key]
        rows.append({
            "campaign": campaign,
            "architecture": architecture,
            "scenario": "P00",
            "precision": value["precision"],
            "recall": value["recall"],
            "f1_score": value["f1_score"],
            "comparison_status": "directly_comparable",
        })
    path = OUTPUT / "v1_vs_v2_nominal_quality.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


def selected_font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(
            str(Path("/System/Library/Fonts/Supplemental") / name), size
        )
    except OSError:
        return ImageFont.load_default()


def centered(draw, text, x, y, chosen_font, fill="#172033"):
    bounds = draw.textbbox((0, 0), text, font=chosen_font)
    draw.text((x - (bounds[2] - bounds[0]) / 2, y), text, font=chosen_font, fill=fill)


def build_plot(summary):
    image = Image.new("RGB", (1800, 1200), "white")
    draw = ImageDraw.Draw(image)
    ink, muted = "#172033", "#667085"
    blue, cyan, green, orange = "#2563eb", "#0891b2", "#16a34a", "#f59e0b"
    centered(draw, "Benchmark V1 vs Benchmark V2", 900, 35, selected_font(44, True))
    centered(draw, "Résultats communs et extension du protocole", 900, 95, selected_font(22), muted)

    # Shared nominal F1 values.
    quality = summary["directly_comparable_nominal_entity_quality"]
    values = [
        ("V1 baseline", quality["benchmark_v1_baseline"]["f1_score"], blue),
        ("V1 sémantique", quality["benchmark_v1_semantic"]["f1_score"], cyan),
        ("V2 A1", quality["benchmark_v2_A1"]["f1_score"], green),
        ("V2 A2", quality["benchmark_v2_A2"]["f1_score"], orange),
    ]
    draw.text((100, 165), "Qualité nominale directement comparable — P00", font=selected_font(25, True), fill=ink)
    baseline = 545
    draw.line((100, baseline, 1020, baseline), fill=ink, width=2)
    for index, (label, value, color) in enumerate(values):
        x = 210 + index * 235
        height = int(value * 300)
        draw.rectangle((x - 65, baseline - height, x + 65, baseline), fill=color)
        centered(draw, f"F1 {value:.3f}", x, baseline - height / 2 - 12, selected_font(18, True), "white")
        centered(draw, label, x, 570, selected_font(17, True), ink)

    # Coverage comparison.
    draw.text((1120, 165), "Couverture expérimentale", font=selected_font(25, True), fill=ink)
    coverage = [("V1", 6, 0, blue), ("V2", 6, 5, green)]
    for index, (label, structural, semantic, color) in enumerate(coverage):
        y = 280 + index * 170
        draw.text((1135, y), label, font=selected_font(22, True), fill=ink)
        draw.rectangle((1230, y, 1230 + structural * 65, y + 42), fill=color)
        draw.text((1245, y + 8), f"{structural} structurels", font=selected_font(16, True), fill="white")
        if semantic:
            draw.rectangle((1230, y + 56, 1230 + semantic * 65, y + 98), fill=orange)
            draw.text((1245, y + 64), f"{semantic} sémantiques", font=selected_font(16, True), fill="white")
        else:
            draw.text((1230, y + 64), "0 scénario sémantique", font=selected_font(16), fill=muted)

    # V2-only semantic robustness.
    draw.line((90, 690, 1710, 690), fill="#d0d5dd", width=2)
    draw.text((100, 735), "Apport mesuré uniquement par V2 — scénarios S01–S05", font=selected_font(25, True), fill=ink)
    architectures = summary["v2_semantic_scenario_results"]
    columns = [("A0", blue), ("A1", cyan), ("A2", orange), ("A3", green)]
    for index, (name, color) in enumerate(columns):
        item = architectures[name]
        x = 270 + index * 420
        centered(draw, name, x, 800, selected_font(24, True), ink)
        centered(draw, f"résultat initial {item['initial_mean_outcome']:.2f}", x, 850, selected_font(18), color)
        centered(draw, f"résultat final {item['final_mean_outcome']:.2f}", x, 890, selected_font(18, True), color)
        centered(draw, f"{item['silent_wrong_acceptances']} erreurs initiales silencieuses", x, 930, selected_font(17), "#dc2626" if item["silent_wrong_acceptances"] else green)
        centered(draw, f"{item['initial_human_reviews']} revues humaines", x, 970, selected_font(17), muted)

    draw.rounded_rectangle((160, 1060, 1640, 1150), radius=10, fill="#eff6ff")
    centered(draw, "Conclusion : V2 ne gagne pas en F1 nominal ; il étend la recherche à A0–A3 et aux ambiguïtés sémantiques.", 900, 1088, selected_font(19, True), blue)
    return image


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    PLOTS.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    summary = build_summary()
    summary_path = OUTPUT / "v1_vs_v2_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path = write_csv(summary)
    result_plot = PLOTS / "benchmark_v1_vs_v2.png"
    build_plot(summary).save(result_plot)
    image_plot = IMAGES / result_plot.name
    shutil.copy2(result_plot, image_plot)
    for path in (summary_path, csv_path, result_plot, image_plot):
        print(path)
    return summary


if __name__ == "__main__":
    run()
