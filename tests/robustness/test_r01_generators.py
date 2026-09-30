import json

import pytest

from src.robustness.r01.generators import generate_case


@pytest.mark.parametrize("scenario", ["S01", "S04", "S05"])
@pytest.mark.parametrize("intensity", ["I0", "I1", "I2"])
def test_r01_generation_is_byte_deterministic(tmp_path, scenario, intensity):
    left = tmp_path / "left"
    right = tmp_path / "right"
    generate_case(left, scenario, intensity, seed=11)
    generate_case(right, scenario, intensity, seed=11)

    left_files = {str(path.relative_to(left)): path.read_bytes() for path in left.rglob("*") if path.is_file()}
    right_files = {str(path.relative_to(right)): path.read_bytes() for path in right.rglob("*") if path.is_file()}
    assert left_files == right_files


def test_r01_seeds_produce_distinct_data(tmp_path):
    left = tmp_path / "seed-11"
    right = tmp_path / "seed-22"
    generate_case(left, "S05", "I1", seed=11)
    generate_case(right, "S05", "I1", seed=22)

    assert (left / "raw/mixed_events.csv").read_bytes() != (right / "raw/mixed_events.csv").read_bytes()


def test_r01_s04_intensity_controls_exact_drift(tmp_path):
    for intensity, expected in (("I0", 5), ("I1", 15), ("I2", 40)):
        destination = tmp_path / intensity
        generate_case(destination, "S04", intensity, seed=11)
        manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["parameters"]["drift_points"] == expected


def test_r01_s05_intensity_controls_ticket_share(tmp_path):
    for intensity, expected in (("I0", 0.10), ("I1", 0.50), ("I2", 0.90)):
        destination = tmp_path / intensity
        generate_case(destination, "S05", intensity, seed=11)
        manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["parameters"]["ticket_share"] == expected


def test_r01_rejects_writing_into_a_non_empty_directory(tmp_path):
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "existing.txt").write_text("historical", encoding="utf-8")

    with pytest.raises(FileExistsError):
        generate_case(destination, "S01", "I0", seed=11)
    assert (destination / "existing.txt").read_text(encoding="utf-8") == "historical"


def test_r01_protocol_parameters_are_frozen(tmp_path):
    with pytest.raises(ValueError, match="100 entités"):
        generate_case(tmp_path / "wrong-size", "S01", "I0", seed=11, size=1000)
    with pytest.raises(ValueError, match="5 %"):
        generate_case(tmp_path / "wrong-noise", "S01", "I0", seed=11, noise_rate=0.10)
    with pytest.raises(ValueError, match="Graine"):
        generate_case(tmp_path / "wrong-seed", "S01", "I0", seed=44)
