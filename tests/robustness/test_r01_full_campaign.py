from src.robustness.r01.run_full_campaign import aggregate


def test_aggregate_keeps_calibration_out_of_statistics():
    rows = []
    for seed, subset, score in ((11, "calibration", 0.0), (22, "test", 1.0), (33, "test", 1.0)):
        for scenario in ("S01", "S04", "S05"):
            for intensity in ("I0", "I1", "I2"):
                for architecture in ("A0", "A1", "A2", "A3"):
                    rows.append({"seed": seed, "subset": subset, "scenario": scenario,
                                 "intensity": intensity, "architecture": architecture,
                                 "initial_score": score, "final_score": score,
                                 "initial_safe": True, "final_safe": True,
                                 "silent_wrong_acceptances_initial": 0,
                                 "silent_wrong_acceptances_final": 0,
                                 "human_reviews": 0, "adaptation_actions": 0,
                                 "configuration_actions": 0})
    scenario, architecture, intervals = aggregate(rows)
    assert len(scenario) == 36
    assert all(row["test_seeds"] == 2 and row["initial_mean"] == 1.0 for row in scenario)
    assert len(architecture) == 4
    assert len(intervals) == 36
