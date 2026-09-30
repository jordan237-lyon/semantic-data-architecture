from pathlib import Path

import pytest

from src.declarative.model_loader import load_declarative_model
from src.declarative.pipeline import discover_declared_sources
from src.declarative.transformer import DeclarativeTransformationError


def test_a2_rejects_a_discovered_but_undeclared_source(tmp_path):
    model = load_declarative_model()
    for source in ("crm", "support", "finance", "loyalty"):
        (tmp_path / f"{source}.csv").write_text("id\n", encoding="utf-8")

    with pytest.raises(DeclarativeTransformationError, match="loyalty"):
        discover_declared_sources(tmp_path, model)


def test_a2_requires_every_declared_source(tmp_path):
    model = load_declarative_model()
    for source in ("crm", "support"):
        (tmp_path / f"{source}.csv").write_text("id\n", encoding="utf-8")

    with pytest.raises(DeclarativeTransformationError, match="finance"):
        discover_declared_sources(tmp_path, model)
