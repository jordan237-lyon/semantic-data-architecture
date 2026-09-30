"""Scenario discovery and profiling without modifying research artefacts."""

from pathlib import Path

import pandas as pd

from app.contracts import Scenario, Source
from src.semantic.profiler import profile_csv


ROOT = Path(__file__).resolve().parents[2]

SCENARIOS = {
    "P00": Scenario(
        identifier="P00",
        title="Exécution nominale",
        raw_directory=ROOT / "data/raw",
        semantic_model=ROOT / "semantic/model.yaml",
        has_ground_truth=True,
    ),
    "S01": Scenario(
        identifier="S01",
        title="Même nom, sens différent",
        raw_directory=ROOT / "data/semantic_scenarios/S01/raw",
        semantic_model=ROOT / "semantic/scenarios/a3_s01_model.yaml",
        has_ground_truth=True,
    ),
    "S02": Scenario(
        identifier="S02",
        title="Noms différents, même sens",
        raw_directory=ROOT / "data/semantic_scenarios/S02/raw",
        semantic_model=ROOT / "semantic/scenarios/a3_s02_model.yaml",
        has_ground_truth=True,
    ),
    "S03": Scenario(
        identifier="S03",
        title="Définitions métier concurrentes",
        raw_directory=ROOT / "data/semantic_scenarios/S03/raw",
        semantic_model=ROOT / "semantic/scenarios/a3_s03_model.yaml",
        has_ground_truth=True,
    ),
    "S04": Scenario(
        identifier="S04",
        title="Dérive sémantique temporelle",
        raw_directory=ROOT / "data/semantic_scenarios/S04/raw",
        semantic_model=ROOT / "semantic/scenarios/a3_s04_model.yaml",
        has_ground_truth=True,
    ),
    "S05": Scenario(
        identifier="S05",
        title="Conflit entre nom, type et valeurs",
        raw_directory=ROOT / "data/semantic_scenarios/S05/raw",
        semantic_model=ROOT / "semantic/scenarios/a3_s05_model.yaml",
        has_ground_truth=True,
    ),
}


def list_scenarios() -> list[Scenario]:
    return list(SCENARIOS.values())


def get_scenario(identifier: str) -> Scenario:
    try:
        scenario = SCENARIOS[identifier.upper()]
    except KeyError as error:
        raise ValueError(f"Scénario inconnu : {identifier}") from error
    if not scenario.raw_directory.is_dir():
        raise FileNotFoundError(f"Données absentes pour {scenario.identifier}")
    if not scenario.semantic_model.is_file():
        raise FileNotFoundError(f"Modèle absent pour {scenario.identifier}")
    return scenario


def list_sources(identifier: str) -> list[Source]:
    scenario = get_scenario(identifier)
    sources = []
    for path in sorted(scenario.raw_directory.glob("*.csv")):
        frame = pd.read_csv(path)
        sources.append(Source(path.stem, path, len(frame), len(frame.columns)))
    return sources


def profile_scenario(identifier: str) -> list[dict]:
    scenario = get_scenario(identifier)
    profiles = []
    for source in list_sources(identifier):
        profiles.extend(profile_csv(source.path, source.name))
    return profiles

