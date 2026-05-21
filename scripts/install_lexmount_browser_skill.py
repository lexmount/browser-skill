#!/usr/bin/env python3
"""Install the lexmount-browser skill into Codex and/or Claude Code."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL = REPO_ROOT / "skills" / "lexmount-browser"


def _target_dirs(target: str) -> list[Path]:
    home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex"))
    targets = {
        "codex": codex_home / "skills" / "lexmount-browser",
        "claude": home / ".claude" / "skills" / "lexmount-browser",
    }
    if target == "both":
        return [targets["codex"], targets["claude"]]
    return [targets[target]]


def _copy_skill(destination: Path, *, force: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if not force:
            raise SystemExit(
                f"{destination} already exists. Re-run with --force to replace it."
            )
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_SKILL, destination)


def _write_env(destination: Path) -> None:
    values = {
        "LEXMOUNT_API_KEY": os.environ.get("LEXMOUNT_API_KEY"),
        "LEXMOUNT_PROJECT_ID": os.environ.get("LEXMOUNT_PROJECT_ID"),
        "LEXMOUNT_BASE_URL": os.environ.get("LEXMOUNT_BASE_URL"),
    }
    lines: list[str] = []
    for key, value in values.items():
        if not value:
            continue
        if "\n" in value or "\r" in value:
            raise SystemExit(f"Refusing to write {key}: value contains a newline")
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}="{escaped}"')
    if lines:
        (destination / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bootstrap(destination: Path) -> None:
    subprocess.check_call(
        [sys.executable, str(destination / "scripts" / "bootstrap_runtime.py")]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        choices=("codex", "claude", "both"),
        default="both",
        help="Install destination",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing skill")
    parser.add_argument(
        "--write-env-from-current",
        action="store_true",
        help="Write current Lexmount env vars into the installed skill .env",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Create the installed skill venv and install lex-browser-runtime[skill]",
    )
    args = parser.parse_args(argv)

    if not SOURCE_SKILL.exists():
        raise SystemExit(f"Source skill not found: {SOURCE_SKILL}")

    installed: list[Path] = []
    for destination in _target_dirs(args.target):
        _copy_skill(destination, force=args.force)
        if args.write_env_from_current:
            _write_env(destination)
        if args.bootstrap:
            _bootstrap(destination)
        installed.append(destination)

    for destination in installed:
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
