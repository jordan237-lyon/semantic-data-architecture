"""Consolidate heterogeneous S01-S05 outcomes into an auditable benchmark table."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/benchmark_v2"
OUTPUT = RESULTS / "semantic_benchmark"


def load(scenario):
    return json.loads((RESULTS / scenario / "summary.json").read_text(encoding="utf-8"))["architectures"]


def base_row(scenario, architecture, state="initial"):
    return {
        "scenario": scenario,
        "architecture": architecture,
        "state": state,
        "outcome_score": 0.0,
        "safe_handling": False,
        "human_reviews": 0,
        "silent_wrong_acceptances": 0,
        "adaptation_actions": 0,
        "measurement_basis": "",
    }


def normalized_rows():
    rows = []
    for scenario in ("S01", "S02", "S03"):
        architectures = load(scenario)
        quality_key = "semantic_quality" if scenario == "S03" else "schema_quality"
        for architecture, result in architectures.items():
            quality = result[quality_key]
            row = base_row(scenario, architecture)
            row.update({
                "outcome_score": quality["f1_score"],
                "safe_handling": quality.get("accepted_incorrect", 0) == 0,
                "human_reviews": result.get("human_reviews_required", quality.get("review_mappings", 0)),
                "silent_wrong_acceptances": quality.get("accepted_incorrect", 0),
                "measurement_basis": "schema_mapping_f1",
            })
            rows.append(row)

    architectures = load("S04")
    for architecture, result in architectures.items():
        states = [("initial", result)]
        if architecture == "A2":
            states = [("initial", result["before_adaptation"]), ("adapted", result["after_adaptation"])]
        for state, current in states:
            row = base_row("S04", architecture, state)
            row.update({
                "outcome_score": 1.0 if current["safe_handling"] else 0.0,
                "safe_handling": current["safe_handling"],
                "human_reviews": current.get("human_reviews_required", 0),
                "silent_wrong_acceptances": current["silent_wrong_acceptances"],
                "adaptation_actions": current["adaptation_actions"],
                "measurement_basis": "safe_drift_handling",
            })
            rows.append(row)

    architectures = load("S05")
    for architecture, result in architectures.items():
        states = [("initial", result)]
        if architecture == "A2":
            states = [("initial", result["before_adaptation"]), ("adapted", result["after_adaptation"])]
        for state, current in states:
            row = base_row("S05", architecture, state)
            quality = current.get("value_quality")
            safe_review = current.get("safe_handling", False) and current.get("human_reviews_required", 0) > 0
            row.update({
                "outcome_score": 1.0 if safe_review else quality["f1_score"],
                "safe_handling": current["safe_handling"],
                "human_reviews": current.get("human_reviews_required", 0),
                "silent_wrong_acceptances": current["silent_wrong_acceptances"],
                "adaptation_actions": current["adaptation_actions"],
                "measurement_basis": "safe_review" if safe_review else "row_level_f1",
            })
            rows.append(row)
    return rows


def architecture_summary(rows):
    initial = [row for row in rows if row["state"] == "initial"]
    final = [row for row in rows if row["state"] == "adapted"]
    summaries = []
    for architecture in ("A0", "A1", "A2", "A3"):
        architecture_rows = [row for row in initial if row["architecture"] == architecture]
        final_by_scenario = {row["scenario"]: row for row in architecture_rows}
        for row in final:
            if row["architecture"] == architecture:
                final_by_scenario[row["scenario"]] = row
        summaries.append({
            "architecture": architecture,
            "initial_mean_outcome": round(sum(row["outcome_score"] for row in architecture_rows) / 5, 6),
            "final_mean_outcome": round(sum(row["outcome_score"] for row in final_by_scenario.values()) / 5, 6),
            "initial_safe_scenarios": sum(bool(row["safe_handling"]) for row in architecture_rows),
            "final_safe_scenarios": sum(bool(row["safe_handling"]) for row in final_by_scenario.values()),
            "initial_human_reviews": sum(int(row["human_reviews"]) for row in architecture_rows),
            "silent_wrong_acceptances": sum(int(row["silent_wrong_acceptances"]) for row in architecture_rows),
            "post_detection_adaptation_actions": sum(
                int(row["adaptation_actions"])
                for row in final if row["architecture"] == architecture
            ),
        })
    return summaries


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run():
    rows = normalized_rows()
    summaries = architecture_summary(rows)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "scenario_results.csv", rows)
    write_csv(OUTPUT / "architecture_summary.csv", summaries)
    (OUTPUT / "benchmark_summary.json").write_text(
        json.dumps({
            "scope": ["S01", "S02", "S03", "S04", "S05"],
            "normalization": {
                "S01-S03": "F1 des mappings acceptés",
                "S04": "1 si la dérive est traitée sans acceptation silencieuse, sinon 0",
                "S05": "F1 ligne par ligne, ou 1 pour une revue sûre empêchant un mapping unique invalide",
            },
            "architectures": summaries,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    conclusions = """# Conclusions du benchmark sémantique S01–S05

## Résultat principal

Aucune architecture ne domine sur toutes les dimensions. A0 et A2 atteignent une qualité finale parfaite lorsque les règles nécessaires sont fournies. Leur faiblesse apparaît lors des changements non anticipés : A2 accepte silencieusement une ancienne définition dans S04 et un identifiant mal nommé dans S05 avant adaptation.

A1 couvre correctement la découverte technique et peut signaler une dérive de distribution, mais ne résout pas les ambiguïtés métier. Dans S05, l'absence de contrôle sémantique conduit à 70 erreurs silencieuses.

A3 obtient le meilleur compromis de sécurité sans adaptation post-détection : il automatise S02 et S03, et dirige S01, S04 et S05 vers une revue lorsque la marge ou le contexte ne permettent pas une acceptation sûre. Sa contrepartie est une couverture automatique plus faible et la nécessité de maintenir le modèle et les politiques sémantiques.

## Limites d'interprétation

- Les scores consolidés combinent des tâches différentes ; ils servent à résumer, pas à remplacer les métriques détaillées.
- Les scénarios sont synthétiques et de taille limitée.
- Les déclarations et politiques spécifiques aux scénarios constituent elles-mêmes un coût de préparation, même lorsqu'aucune adaptation post-détection n'est comptée.
- Les temps d'exécution ne sont pas interprétables comme un benchmark de performance à cette échelle.
- Une campagne répétée sur plusieurs graines, volumes et niveaux de bruit est nécessaire avant toute généralisation.
"""
    (OUTPUT / "conclusions.md").write_text(conclusions, encoding="utf-8")
    print(json.dumps(summaries, indent=2, ensure_ascii=False))
    return summaries


if __name__ == "__main__":
    run()
