"""Generate only the frozen R01 calibration datasets (seed 11)."""

import json

from src.robustness.r01.generators import INTENSITIES, SCENARIOS, generate_case
from src.robustness.r01.paths import DATA_ROOT


CALIBRATION_SEED = 11


def run():
    manifests = []
    for scenario in SCENARIOS:
        for intensity in INTENSITIES:
            destination = DATA_ROOT / scenario / intensity / f"seed-{CALIBRATION_SEED}"
            manifests.append(
                generate_case(destination, scenario, intensity, CALIBRATION_SEED)
            )
    print(json.dumps({
        "campaign": "R01",
        "subset": "calibration",
        "seed": CALIBRATION_SEED,
        "datasets_generated": len(manifests),
    }, indent=2, ensure_ascii=False))
    return manifests


if __name__ == "__main__":
    run()

