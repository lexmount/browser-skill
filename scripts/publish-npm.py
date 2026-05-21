#!/usr/bin/env python3
"""Validate and optionally publish the Lexmount browser skill npm installer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from shutil import which


def resolve_command(command: str) -> str:
    """Resolve an executable name across POSIX and Windows shells."""

    path = which(command)
    if path:
        return path
    if sys.platform == "win32":
        path = which(f"{command}.cmd")
        if path:
            return path
    return command


def run_step(
    name: str,
    command: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one release validation step."""

    print()
    print(f"==> {name}")
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        env=env,
        capture_output=capture_output,
    )


def load_package_metadata(root: Path) -> tuple[str, str]:
    package_json = root / "package.json"
    data = json.loads(package_json.read_text(encoding="utf-8"))
    return data["name"], data["version"]


def assert_version_not_published(
    root: Path, npm: str, package_name: str, version: str
) -> None:
    print()
    print("==> Checking npm version availability")
    result = subprocess.run(
        [npm, "view", f"{package_name}@{version}", "version"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode == 0:
        raise RuntimeError(f"{package_name}@{version} is already published on npm.")

    combined = f"{result.stdout or ''}\n{result.stderr or ''}"
    if (
        "E404" in combined
        or "404" in combined
        or "not in this registry" in combined.lower()
    ):
        print(f"{package_name}@{version} is not published yet.")
        return

    raise RuntimeError(
        f"Failed to check whether the npm version already exists.\n{combined.strip()}"
    )


def smoke_install_env(root: Path, temp_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "CODEX_HOME": str(temp_dir / "codex-home"),
            "HOME": str(temp_dir / "home"),
            "LEXMOUNT_INSTALL_NONINTERACTIVE": "1",
            "LEXMOUNT_INSTALL_TARGET": "both",
            "LEXMOUNT_INSTALL_REGION": "china",
            "LEXMOUNT_INSTALL_DEPS": "0",
            "LEXMOUNT_API_KEY": "test-key#fragment",
            "LEXMOUNT_PROJECT_ID": "test-project",
            "LEX_BROWSER_RUNTIME_NO_BOOTSTRAP": "1",
            "PATH": f"{root / '.venv' / 'bin'}{os.pathsep}{env.get('PATH', '')}",
        }
    )
    return env


def assert_smoke_install_outputs(temp_dir: Path) -> None:
    targets = [
        temp_dir / "codex-home" / "skills" / "lexmount-browser",
        temp_dir / "home" / ".claude" / "skills" / "lexmount-browser",
    ]
    for target in targets:
        if not (target / "SKILL.md").exists():
            raise RuntimeError(f"Installed skill missing SKILL.md: {target}")
        env_text = (target / ".env").read_text(encoding="utf-8")
        if 'LEXMOUNT_API_KEY="test-key#fragment"' not in env_text:
            raise RuntimeError(f"Installed skill missing API key in .env: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run npm release checks and optionally publish the skill package."
    )
    parser.add_argument(
        "--skip-publish",
        action="store_true",
        help="Run validation only and skip `npm publish`.",
    )
    parser.add_argument(
        "--skip-login-check",
        action="store_true",
        help="Skip `npm whoami`. Required for CI trusted publishing.",
    )
    parser.add_argument(
        "--skip-version-check",
        action="store_true",
        help="Skip checking whether the package version is already published.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    npm = resolve_command("npm")
    node = resolve_command("node")
    python = resolve_command("python")
    package_name, version = load_package_metadata(root)

    if not args.skip_login_check:
        run_step("Checking npm login", [npm, "whoami"], root)
    else:
        print()
        print("==> Skipping npm login check")

    if not args.skip_version_check:
        assert_version_not_published(root, npm, package_name, version)
    else:
        print()
        print("==> Skipping npm version availability check")

    run_step("Installing npm dependencies", [npm, "ci"], root)
    run_step(
        "Checking installer syntax",
        [node, "--check", "./tools/install-skill.mjs"],
        root,
    )
    run_step(
        "Checking Windows installer syntax",
        [node, "--check", "./tools/install-skill-win.mjs"],
        root,
    )
    run_step(
        "Smoke checking installer help",
        [node, "./tools/install-skill.mjs", "--help"],
        root,
    )
    run_step(
        "Checking skill bootstrap syntax",
        [
            python,
            "-m",
            "py_compile",
            "./skills/lexmount-browser/scripts/bootstrap_runtime.py",
        ],
        root,
    )

    with tempfile.TemporaryDirectory(prefix="lex-browser-skill-npm-") as raw_temp:
        temp_dir = Path(raw_temp)
        run_step(
            "Smoke installing skill without dependency bootstrap",
            [node, "./tools/install-skill.mjs"],
            root,
            env=smoke_install_env(root, temp_dir),
        )
        assert_smoke_install_outputs(temp_dir)

    run_step("Validating package contents", [npm, "pack", "--dry-run"], root)

    if args.skip_publish:
        print()
        print("Skipped npm publish. Validation completed.")
        return 0

    run_step("Publishing package to npm", [npm, "publish"], root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, end="", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, end="", file=sys.stderr)
        raise SystemExit(exc.returncode)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
