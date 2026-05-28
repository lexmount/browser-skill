#!/usr/bin/env python3
"""Bootstrap lex-browser-runtime for the installed lexmount-browser skill."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import venv
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
VENV_DIR = SKILL_DIR / ".venv"
RUNTIME_REQUIREMENT_FILENAME = "runtime-requirement.txt"
DEFAULT_GIT_REQUIREMENT = (
    "lex-browser-runtime[skill] @ git+https://github.com/lexmount/browser-skill.git"
)


def _venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _runtime_requirement() -> str:
    if (REPO_ROOT / "pyproject.toml").exists() and (
        REPO_ROOT / "lex_browser_runtime"
    ).is_dir():
        return f"{REPO_ROOT}[skill]"
    runtime_requirement = SKILL_DIR / RUNTIME_REQUIREMENT_FILENAME
    if runtime_requirement.exists():
        return runtime_requirement.read_text(encoding="utf-8").strip()
    return DEFAULT_GIT_REQUIREMENT


def _install_requirement(python: Path, requirement: str) -> None:
    uv = shutil.which("uv")
    if uv:
        subprocess.check_call(
            [uv, "pip", "install", "--python", str(python), requirement]
        )
        return
    subprocess.check_call([str(python), "-m", "pip", "install", requirement])


def bootstrap(*, force: bool = False) -> Path:
    """Create the skill-local venv and install lex-browser-runtime."""

    if force and VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)
    if not VENV_DIR.exists():
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    python = _venv_python()
    if not python.exists():
        raise SystemExit(f"Python executable not found in {VENV_DIR}")

    _install_requirement(python, _runtime_requirement())
    return python


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Recreate the venv")
    args = parser.parse_args(argv)

    python = bootstrap(force=args.force)
    print(python)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
