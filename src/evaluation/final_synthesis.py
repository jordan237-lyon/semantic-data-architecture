"""Aggregate all experiments into the final scientific synthesis."""

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
FINAL = RESULTS / "final"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def build_summary():
    baseline = load("results/baseline/baseline_evaluation.json")["overall"]
    semantic = load("results/semantic/pipeline/semantic_evaluation.json")["overall"]
    benchmark = load("results/comparison/benchmark_summary.json")["performance"]
    p01 = load("results/perturbations/p01_renamed_column/results.json")
    p02_before = load("results/perturbations/p02_country_format/before_adaptation/results.json")
    p02_after = load("results/perturbations/p02_country_format/results.json")
    p03_before = load("results/perturbations/p03_merged_name_columns/before_adaptation/results.json")
    p03_after = load("results/perturbations/p03_merged_name_columns/results.json")
    scale_before = load("results/scale/before_null_fix/scale_results.json")
    scale_after = load("results/scale/scale_results.json")
    loyalty_before = load("results/new_source/loyalty/before_adaptation/results.json")
    loyalty_after = load("results/new_source/loyalty/after_adaptation/results.json")

    before_x10 = next(
        row for row in scale_before["results"]
        if row["scale_factor"] == 10 and row["pipeline"] == "baseline"
    )
    after_x10 = next(
        row for row in scale_after["results"]
        if row["scale_factor"] == 10 and row["pipeline"] == "baseline"
    )
    matrix = [
        {
            "experiment": "Nominal quality", "change": "Three original sources",
            "baseline_outcome": "success", "semantic_outcome": "success",
            "baseline_effort": "19 mappings; 12 rules",
            "semantic_effort": "17 automatic; 2 validations",
            "baseline_metric": baseline["f1_score"], "semantic_metric": semantic["f1_score"],
        },
        {
            "experiment": "P01 renamed column", "change": "support.mail -> customer_email_address",
            "baseline_outcome": "failed before code adaptation", "semantic_outcome": "success after 1 validation",
            "baseline_effort": "code adaptation required", "semantic_effort": "1 incremental validation; 0 code",
            "baseline_metric": "failed", "semantic_metric": p01["semantic"]["entity_quality"]["f1_score"],
        },
        {
            "experiment": "P02 value format", "change": "country codes -> lowercase names",
            "baseline_outcome": "0% -> 100% conformity", "semantic_outcome": "0% -> 100% conformity",
            "baseline_effort": "1 Python rule", "semantic_effort": "7 YAML vocabulary entries",
            "baseline_metric": p02_after["baseline"]["value_quality"]["country_conformity"],
            "semantic_metric": p02_after["semantic"]["value_quality"]["country_conformity"],
        },
        {
            "experiment": "P03 merged columns", "change": "first_name + last_name -> customer_name",
            "baseline_outcome": "failed -> success", "semantic_outcome": "automatic success",
            "baseline_effort": "1 Python rule", "semantic_effort": "0 change; 0 validation",
            "baseline_metric": p03_after["baseline"]["entity_quality"]["f1_score"],
            "semantic_metric": p03_after["semantic"]["entity_quality"]["f1_score"],
        },
        {
            "experiment": "Scale x10", "change": "865 -> 8650 source rows",
            "baseline_outcome": "stable after null fix", "semantic_outcome": "stable without change",
            "baseline_effort": "1 Python null-handling rule", "semantic_effort": "0 change",
            "baseline_metric": after_x10["f1_score"], "semantic_metric": next(
                row["f1_score"] for row in scale_after["results"]
                if row["scale_factor"] == 10 and row["pipeline"] == "semantic"
            ),
        },
        {
            "experiment": "Fourth source", "change": "80 Loyalty members; 5 new columns",
            "baseline_outcome": "0% -> 100% coverage", "semantic_outcome": "0% -> 100% coverage",
            "baseline_effort": "5 mappings; 5 rules; 2 Python files",
            "semantic_effort": "4 YAML synonyms; generic orchestration; 0 validation",
            "baseline_metric": loyalty_after["baseline"]["loyalty_quality"]["f1_score"],
            "semantic_metric": loyalty_after["semantic"]["loyalty_quality"]["f1_score"],
        },
    ]
    summary = {
        "objective": "Compare a manual ETL baseline with semantic-assisted integration under identical data changes.",
        "final_nominal_quality": {"baseline": baseline, "semantic": semantic},
        "final_performance": benchmark,
        "experiments": matrix,
        "key_findings": [
            "After correcting null matching, both approaches reach the same nominal entity F1 of 0.978558.",
            "The semantic pipeline costs 5.206608x the baseline wall time and 1.386861x its measured Python peak memory on nominal data.",
            "Semantic metadata turns P01 into a review decision and absorbs P03 automatically, while the baseline fails before code adaptation.",
            "P02 requires adaptation in both approaches: imperative Python for the baseline and declarative YAML for semantics.",
            f"At x10, the baseline F1 improves from {before_x10['f1_score']:.6f} to {after_x10['f1_score']:.6f} after fixing null joins.",
            "The fourth source reaches perfect CRM-Loyalty matching in both approaches; semantic mappings are automatic after vocabulary and generic-orchestration improvements.",
        ],
        "limitations": [
            "Synthetic datasets and one business domain limit external validity.",
            "Entity matching relies on exact normalized e-mail and does not test probabilistic identity resolution.",
            "Performance was measured on one machine with small-to-medium datasets and Python allocation memory only.",
            "Effort counts rules, mappings, validations and changed artifacts, not human working time.",
            "The semantic vocabulary was curated with knowledge of the domain, so results do not represent zero-knowledge onboarding.",
            "The fourth-source semantic path required a one-time generic orchestration refactor in addition to YAML enrichment.",
        ],
        "unused_checks": {
            "p02_before_conformity": p02_before["semantic"]["value_quality"]["country_conformity"],
            "p03_baseline_before": p03_before["baseline"]["status"],
            "loyalty_coverage_before": loyalty_before["semantic"]["source_coverage"],
        },
    }
    return summary


def _font(size, bold=False):
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    try:
        return ImageFont.truetype(str(Path("/System/Library/Fonts/Supplemental") / name), size)
    except OSError:
        return ImageFont.load_default()


def write_dashboard(summary):
    image = Image.new("RGB", (1700, 1200), "white")
    draw = ImageDraw.Draw(image)
    ink, muted, blue, gray, green, orange = "#172033", "#667085", "#2563eb", "#64748b", "#16a34a", "#f59e0b"

    def center(text, x, y, font, fill=ink):
        width = draw.textbbox((0, 0), text, font=font)[2]
        draw.text((x - width / 2, y), text, font=font, fill=fill)

    center("Synthèse expérimentale — ETL classique vs sémantique", 850, 35, _font(40, True))
    center("Qualité · adaptation · passage à l’échelle · nouvelle source", 850, 95, _font(22), muted)
    baseline = summary["final_nominal_quality"]["baseline"]
    semantic = summary["final_nominal_quality"]["semantic"]
    performance = summary["final_performance"]
    cards = [
        ("F1 nominal", f"{baseline['f1_score']:.3f}", f"{semantic['f1_score']:.3f}"),
        ("Temps médian", f"{performance['baseline']['wall_time_seconds']['median']*1000:.1f} ms", f"{performance['semantic']['wall_time_seconds']['median']*1000:.1f} ms"),
        ("Mémoire Python", f"{performance['baseline']['python_peak_memory_bytes']['median']/1e6:.2f} Mo", f"{performance['semantic']['python_peak_memory_bytes']['median']/1e6:.2f} Mo"),
    ]
    for index, (title, base_value, sem_value) in enumerate(cards):
        x = 100 + index * 530
        draw.rounded_rectangle((x, 165, x + 450, 360), radius=10, fill="#f8fafc", outline="#d8dee9")
        center(title, x + 225, 195, _font(25, True))
        center(base_value, x + 120, 260, _font(32, True), gray)
        center(sem_value, x + 335, 260, _font(32, True), blue)
        center("Baseline", x + 120, 315, _font(17), muted)
        center("Sémantique", x + 335, 315, _font(17), muted)
    center("Résilience et effort observés", 850, 420, _font(30, True))
    rows = [
        ("P01 · renommage", "Code requis", "1 validation", orange),
        ("P02 · format pays", "1 règle Python", "7 entrées YAML", orange),
        ("P03 · colonnes fusionnées", "1 règle Python", "Automatique", green),
        ("Échelle 10×", "F1 stable après correction", "F1 stable", green),
        ("4e source Loyalty", "5 mappings + 5 règles", "4 synonymes + orchestration", blue),
    ]
    y = 490
    draw.text((125, y), "Expérience", font=_font(21, True), fill=ink)
    draw.text((650, y), "Baseline", font=_font(21, True), fill=gray)
    draw.text((1120, y), "Sémantique", font=_font(21, True), fill=blue)
    for label, base, sem, color in rows:
        y += 82
        draw.line((110, y - 20, 1590, y - 20), fill="#e5e7eb", width=2)
        draw.ellipse((125, y + 2, 143, y + 20), fill=color)
        draw.text((165, y), label, font=_font(21, True), fill=ink)
        draw.text((650, y), base, font=_font(20), fill=ink)
        draw.text((1120, y), sem, font=_font(20), fill=ink)
    draw.rounded_rectangle((120, 970, 1580, 1125), radius=10, fill="#fef3c7")
    center("Conclusion", 850, 990, _font(25, True))
    center("La baseline reste plus rapide. La sémantique apporte surtout de la valeur lorsque les schémas évoluent", 850, 1040, _font(20, True))
    center("ou que de nouvelles sources proches du vocabulaire métier doivent être intégrées.", 850, 1075, _font(20, True))
    path = FINAL / "plots" / "global_dashboard.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def run():
    summary = build_summary()
    FINAL.mkdir(parents=True, exist_ok=True)
    (FINAL / "global_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (FINAL / "experiment_matrix.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary["experiments"][0]))
        writer.writeheader()
        writer.writerows(summary["experiments"])
    write_dashboard(summary)
    print(FINAL / "global_summary.json")
    print(FINAL / "experiment_matrix.csv")
    print(FINAL / "plots" / "global_dashboard.png")
    return summary


if __name__ == "__main__":
    run()
