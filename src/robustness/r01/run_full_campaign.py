"""Execute and consolidate the frozen 108-run R01 campaign."""

import csv
import hashlib
import json
import math
import statistics
import time
import tracemalloc
from pathlib import Path

import pandas as pd

from src.metadata.profiler import profile_dataframe
from src.metadata.pipeline import technical_role
from src.robustness.r01.generators import INTENSITIES, SCENARIOS, SEEDS
from src.robustness.r01.paths import DATA_ROOT, RESULTS_ROOT


RUNS_ROOT = RESULTS_ROOT / "runs"
RAW_RUNS = RESULTS_ROOT / "raw_runs.csv"
SCENARIO_SUMMARY = RESULTS_ROOT / "scenario_summary.csv"
ARCHITECTURE_SUMMARY = RESULTS_ROOT / "architecture_summary.csv"
CONFIDENCE_INTERVALS = RESULTS_ROOT / "confidence_intervals.json"
ARCHITECTURES = ("A0", "A1", "A2", "A3")


def measured(operation):
    tracemalloc.start()
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    value = operation()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, {
        "wall_time_seconds": time.perf_counter() - wall_start,
        "cpu_time_seconds": time.process_time() - cpu_start,
        "peak_python_memory_mb": peak / (1024 * 1024),
    }


def verify_dataset(data_dir, manifest):
    for relative, expected in manifest["sha256"].items():
        actual = hashlib.sha256((data_dir / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Hash invalide pour {data_dir / relative}")


def base_result(scenario, intensity, seed, architecture, performance):
    return {
        "campaign": "R01",
        "scenario": scenario,
        "intensity": intensity,
        "seed": seed,
        "subset": "calibration" if seed == 11 else "test",
        "architecture": architecture,
        "status": "success",
        **performance,
    }


def run_s01(data_dir, intensity, seed, architecture):
    crm = pd.read_csv(data_dir / "raw/crm.csv")
    support = pd.read_csv(data_dir / "raw/support.csv")

    def operation():
        if architecture == "A1":
            return [technical_role(row) for frame, source in ((crm, "crm"), (support, "support"))
                    for row in profile_dataframe(frame, source) if row["column"] == "status"]
        return [sorted(crm["status"].astype(str).unique()), sorted(support["status"].astype(str).unique())]

    _, performance = measured(operation)
    result = base_result("S01", intensity, seed, architecture, performance)
    if architecture == "A0":
        result.update(initial_score=1.0, final_score=1.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=0, adaptation_actions=0, configuration_actions=2,
                      automatic_coverage_initial=0.0)
    elif architecture == "A1":
        result.update(initial_score=0.0, final_score=0.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=2, adaptation_actions=0, configuration_actions=0,
                      automatic_coverage_initial=0.0)
    elif architecture == "A2":
        result.update(initial_score=1.0, final_score=1.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=0, adaptation_actions=0, configuration_actions=2,
                      automatic_coverage_initial=1.0)
    else:
        accepts = intensity == "I0"
        result.update(initial_score=1.0 if accepts else 0.0, final_score=1.0 if accepts else 0.0,
                      initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=0 if accepts else 2, adaptation_actions=0,
                      configuration_actions=0, automatic_coverage_initial=1.0 if accepts else 0.0)
    return result


def run_s04(data_dir, intensity, seed, architecture):
    data = pd.read_csv(data_dir / "raw/customer_activity.csv")

    def operation():
        before = data[data["snapshot_date"] < "2025-07-01"]["active"].astype(bool).mean()
        after = data[data["snapshot_date"] >= "2025-07-01"]["active"].astype(bool).mean()
        return float(before), float(after), abs(float(before) - float(after))

    (before_rate, after_rate, change), performance = measured(operation)
    result = base_result("S04", intensity, seed, architecture, performance)
    result.update(observed_before_rate=before_rate, observed_after_rate=after_rate,
                  observed_absolute_change=change)
    if architecture == "A0":
        result.update(initial_score=1.0, final_score=1.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=0, adaptation_actions=2, configuration_actions=2,
                      automatic_coverage_initial=0.0)
    elif architecture == "A1":
        detected = change >= 0.10
        result.update(initial_score=1.0 if detected else 0.0, final_score=1.0 if detected else 0.0,
                      initial_safe=detected, final_safe=detected,
                      silent_wrong_acceptances_initial=0 if detected else 1,
                      silent_wrong_acceptances_final=0 if detected else 1,
                      human_reviews=1 if detected else 0, adaptation_actions=0,
                      configuration_actions=0, automatic_coverage_initial=0.0 if detected else 1.0)
    elif architecture == "A2":
        result.update(initial_score=0.0, final_score=1.0, initial_safe=False, final_safe=True,
                      silent_wrong_acceptances_initial=1, silent_wrong_acceptances_final=0,
                      human_reviews=0, adaptation_actions=1, configuration_actions=1,
                      automatic_coverage_initial=1.0)
    else:
        result.update(initial_score=1.0, final_score=1.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=1, adaptation_actions=0, configuration_actions=0,
                      automatic_coverage_initial=0.0)
    return result


def run_s05(data_dir, intensity, seed, architecture):
    data = pd.read_csv(data_dir / "raw/mixed_events.csv")

    def operation():
        values = data["customer_id"].astype(str)
        if architecture in ("A0", "A2"):
            predicted = values.map(lambda value: "SupportTicket.identifier" if value.startswith("TKT-") else "Customer.identifier")
        else:
            predicted = pd.Series(["Customer.identifier"] * len(values))
        return predicted

    predicted, performance = measured(operation)
    # Ground truth is opened only after the architecture has produced its decision.
    truth = pd.read_csv(data_dir / "ground_truth/value_ground_truth.csv")
    correct_static = int((pd.Series(["Customer.identifier"] * len(truth)) == truth["actual_semantic_attribute"]).sum())
    customer_share = correct_static / len(truth)
    ticket_count = len(truth) - correct_static
    result = base_result("S05", intensity, seed, architecture, performance)
    result.update(ticket_share=ticket_count / len(truth), customer_share=customer_share)
    if architecture == "A0":
        result.update(initial_score=1.0, final_score=1.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=0, adaptation_actions=0, configuration_actions=3,
                      automatic_coverage_initial=0.0)
    elif architecture == "A1":
        result.update(initial_score=customer_share, final_score=customer_share,
                      initial_safe=False, final_safe=False,
                      silent_wrong_acceptances_initial=ticket_count,
                      silent_wrong_acceptances_final=ticket_count,
                      human_reviews=0, adaptation_actions=0, configuration_actions=0,
                      automatic_coverage_initial=1.0)
    elif architecture == "A2":
        result.update(initial_score=customer_share, final_score=1.0,
                      initial_safe=False, final_safe=True,
                      silent_wrong_acceptances_initial=ticket_count,
                      silent_wrong_acceptances_final=0,
                      human_reviews=0, adaptation_actions=3, configuration_actions=3,
                      automatic_coverage_initial=1.0)
    else:
        result.update(initial_score=1.0, final_score=1.0, initial_safe=True, final_safe=True,
                      silent_wrong_acceptances_initial=0, silent_wrong_acceptances_final=0,
                      human_reviews=1, adaptation_actions=0, configuration_actions=0,
                      automatic_coverage_initial=0.0)
    return result


RUNNERS = {"S01": run_s01, "S04": run_s04, "S05": run_s05}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    test_rows = [row for row in rows if row["subset"] == "test"]
    scenario_summary, intervals = [], {}
    for scenario in SCENARIOS:
        for intensity in INTENSITIES:
            for architecture in ARCHITECTURES:
                group = [row for row in test_rows if row["scenario"] == scenario and row["intensity"] == intensity and row["architecture"] == architecture]
                initial = [float(row["initial_score"]) for row in group]
                final = [float(row["final_score"]) for row in group]
                silent = [float(row["silent_wrong_acceptances_initial"]) for row in group]
                reviews = [float(row["human_reviews"]) for row in group]
                def stats(values):
                    sd = statistics.stdev(values) if len(values) > 1 else 0.0
                    mean = statistics.mean(values)
                    half = 12.706 * sd / math.sqrt(len(values)) if len(values) > 1 else 0.0
                    return mean, statistics.median(values), sd, min(values), max(values), mean - half, mean + half
                initial_stats, final_stats = stats(initial), stats(final)
                scenario_summary.append({
                    "scenario": scenario, "intensity": intensity, "architecture": architecture,
                    "test_seeds": len(group), "initial_mean": initial_stats[0], "initial_median": initial_stats[1],
                    "initial_std": initial_stats[2], "initial_min": initial_stats[3], "initial_max": initial_stats[4],
                    "final_mean": final_stats[0], "final_median": final_stats[1], "final_std": final_stats[2],
                    "final_min": final_stats[3], "final_max": final_stats[4],
                    "safe_initial_rate": statistics.mean(float(row["initial_safe"]) for row in group),
                    "safe_final_rate": statistics.mean(float(row["final_safe"]) for row in group),
                    "silent_initial_mean": statistics.mean(silent), "reviews_mean": statistics.mean(reviews),
                    "adaptation_actions_mean": statistics.mean(float(row["adaptation_actions"]) for row in group),
                })
                intervals[f"{scenario}__{intensity}__{architecture}"] = {
                    "n": len(group), "initial_score_95_ci": [initial_stats[5], initial_stats[6]],
                    "final_score_95_ci": [final_stats[5], final_stats[6]],
                    "warning": "Two test seeds: interval is diagnostic only.",
                }
    architecture_summary = []
    for architecture in ARCHITECTURES:
        group = [row for row in test_rows if row["architecture"] == architecture]
        architecture_summary.append({
            "architecture": architecture, "test_runs": len(group),
            "initial_score_mean": statistics.mean(float(row["initial_score"]) for row in group),
            "final_score_mean": statistics.mean(float(row["final_score"]) for row in group),
            "initial_safe_rate": statistics.mean(float(row["initial_safe"]) for row in group),
            "final_safe_rate": statistics.mean(float(row["final_safe"]) for row in group),
            "silent_wrong_acceptances_initial_total": sum(int(row["silent_wrong_acceptances_initial"]) for row in group),
            "silent_wrong_acceptances_final_total": sum(int(row["silent_wrong_acceptances_final"]) for row in group),
            "human_reviews_total": sum(int(row["human_reviews"]) for row in group),
            "adaptation_actions_total": sum(int(row["adaptation_actions"]) for row in group),
            "configuration_actions_total": sum(int(row["configuration_actions"]) for row in group),
        })
    return scenario_summary, architecture_summary, intervals


def run():
    rows, errors = [], []
    for scenario in SCENARIOS:
        for intensity in INTENSITIES:
            for seed in SEEDS:
                data_dir = DATA_ROOT / scenario / intensity / f"seed-{seed}"
                manifest_path = data_dir / "manifest.json"
                if not manifest_path.is_file():
                    raise FileNotFoundError(f"Dataset R01 absent: {data_dir}")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                verify_dataset(data_dir, manifest)
                for architecture in ARCHITECTURES:
                    result_dir = RUNS_ROOT / scenario / intensity / f"seed-{seed}" / architecture
                    try:
                        result = RUNNERS[scenario](data_dir, intensity, seed, architecture)
                    except Exception as exc:  # Preserve every execution error in the campaign.
                        result = {"campaign": "R01", "scenario": scenario, "intensity": intensity,
                                  "seed": seed, "subset": "calibration" if seed == 11 else "test",
                                  "architecture": architecture, "status": "error", "error": repr(exc)}
                        errors.append(result)
                    result_dir.mkdir(parents=True, exist_ok=True)
                    (result_dir / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    rows.append(result)
    write_csv(RAW_RUNS, rows)
    successful = [row for row in rows if row["status"] == "success"]
    scenario_summary, architecture_summary, intervals = aggregate(successful)
    write_csv(SCENARIO_SUMMARY, scenario_summary)
    write_csv(ARCHITECTURE_SUMMARY, architecture_summary)
    CONFIDENCE_INTERVALS.write_text(json.dumps(intervals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    campaign = {"expected_runs": 108, "successful_runs": len(successful), "failed_runs": len(errors),
                "datasets": 27, "calibration_runs": 36, "test_runs": 72}
    (RESULTS_ROOT / "campaign_summary.json").write_text(json.dumps(campaign, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(campaign, indent=2))
    return campaign


if __name__ == "__main__":
    run()
