from __future__ import annotations

import os
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_is_parseable() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert data["project"]["name"] == "lex-browser-runtime"
    assert data["project"]["requires-python"] == ">=3.11"


def test_agent_skill_links_point_to_shared_ai_skills() -> None:
    assert os.readlink(ROOT / ".claude" / "skills") == "../.ai/skills"
    assert os.readlink(ROOT / ".codex" / "skills") == "../.ai/skills"


def test_plan_directories_exist_for_fresh_clone() -> None:
    assert (ROOT / ".ai" / "superpowers" / "plans" / "active").is_dir()
    assert (ROOT / ".ai" / "superpowers" / "plans" / "completed").is_dir()


def test_makefile_exposes_generic_uv_workflow() -> None:
    makefile = (ROOT / "Makefile").read_text()

    expected_targets = [
        "venv:",
        "deps:",
        "test:",
        "lint:",
        "typecheck:",
        "check:",
        "clean:",
    ]

    for target in expected_targets:
        assert target in makefile

    assert "PYTHON ?= python3.11" in makefile
    assert "uv venv --python $(PYTHON) .venv" in makefile
    assert "uv pip install --python .venv/bin/python -e . --group dev" in makefile
    assert ".venv/bin/python -m pytest" in makefile
    assert ".venv/bin/ruff check ." in makefile
    assert ".venv/bin/mypy ." in makefile
    assert "sync:" not in makefile
    assert "uv sync" not in makefile
    assert "uv run" not in makefile
