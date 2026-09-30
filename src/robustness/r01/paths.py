"""Campaign-specific paths; R01 never writes into historical campaigns."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = ROOT / "config/robustness/R01"
DATA_ROOT = ROOT / "data/robustness/R01"
RESULTS_ROOT = ROOT / "results/robustness/R01"
IMAGES_ROOT = ROOT / "images/robustness/R01"

