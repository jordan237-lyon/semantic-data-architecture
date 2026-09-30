"""Generate the 27 frozen R01 datasets without overwriting existing cases."""

import json

from src.robustness.r01.generators import INTENSITIES, SCENARIOS, SEEDS, generate_case
from src.robustness.r01.paths import DATA_ROOT


def run():
    generated, preserved = [], []
    for scenario in SCENARIOS:
        for intensity in INTENSITIES:
            for seed in SEEDS:
                destination = DATA_ROOT / scenario / intensity / f"seed-{seed}"
                if (destination / "manifest.json").is_file():
                    preserved.append(str(destination.relative_to(DATA_ROOT)))
                    continue
                generate_case(destination, scenario, intensity, seed)
                generated.append(str(destination.relative_to(DATA_ROOT)))
    payload = {
        "campaign": "R01",
        "expected_datasets": 27,
        "generated_now": len(generated),
        "preserved_existing": len(preserved),
        "total_manifests": len(list(DATA_ROOT.glob("S*/I*/seed-*/manifest.json"))),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    run()
