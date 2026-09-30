"""Stable, framework-independent contracts shared by the API and UI."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Scenario:
    identifier: str
    title: str
    raw_directory: Path
    semantic_model: Path
    has_ground_truth: bool

    def public_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["raw_directory"] = str(self.raw_directory)
        payload["semantic_model"] = str(self.semantic_model)
        return payload


@dataclass(frozen=True)
class Source:
    name: str
    path: Path
    row_count: int
    column_count: int

    def public_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        return payload

