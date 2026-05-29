from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install_lexmount_browser_skill.py"
SKILL_DIR = REPO_ROOT / "skills" / "lexmount-browser"
PACKAGE_JSON = REPO_ROOT / "package.json"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"
RUNTIME_REQUIREMENT = SKILL_DIR / "runtime-requirement.txt"


def test_installable_skill_has_runtime_first_instructions() -> None:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    bootstrap = (SKILL_DIR / "scripts" / "bootstrap_runtime.py").read_text(
        encoding="utf-8"
    )

    assert "name: lexmount-browser" in skill
    assert "lex-browser-runtime" in skill
    assert "scripts/lexmount-browser" in skill
    assert "session create" in skill
    assert "case run" in skill
    assert "browser_parallel_limit_reached" in skill
    assert "runtime-requirement.txt" in bootstrap


def test_skill_runtime_requirement_pins_current_release() -> None:
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    requirement = RUNTIME_REQUIREMENT.read_text(encoding="utf-8").strip()

    assert requirement == (
        "lex-browser-runtime[skill] @ "
        f"git+https://github.com/lexmount/browser-skill.git@v{package['version']}"
    )


def test_npm_package_exposes_runtime_backed_skill_installer() -> None:
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))

    assert package["name"] == "@lexmount/browser-skill-installer"
    assert package["bin"] == {
        "lexmount-browser-skill-install": "./tools/install-skill.mjs"
    }
    assert "skills/lexmount-browser/SKILL.md" in package["files"]
    assert "skills/lexmount-browser/runtime-requirement.txt" in package["files"]
    assert "tools/install-skill.mjs" in package["files"]


def test_bootstrap_reads_installed_skill_runtime_requirement(
    tmp_path: Path, monkeypatch
) -> None:
    module_path = SKILL_DIR / "scripts" / "bootstrap_runtime.py"
    spec = importlib.util.spec_from_file_location("bootstrap_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    skill_dir = tmp_path / "lexmount-browser"
    skill_dir.mkdir()
    requirement_path = skill_dir / "runtime-requirement.txt"
    requirement_path.write_text("lex-browser-runtime[skill] @ pinned\n", encoding="utf-8")
    monkeypatch.setattr(module, "SKILL_DIR", skill_dir)
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    assert module._runtime_requirement() == "lex-browser-runtime[skill] @ pinned"

def test_release_versions_are_aligned() -> None:
    package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    package_lock = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert package["version"] == "0.2.3"
    assert package_lock["version"] == package["version"]
    assert package_lock["packages"][""]["version"] == package["version"]
    assert pyproject["project"]["version"] == package["version"]


def test_install_script_copies_codex_and_claude_skill_with_env(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    home = tmp_path / "home"
    env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "HOME": str(home),
        "LEXMOUNT_API_KEY": "key",
        "LEXMOUNT_PROJECT_ID": "project",
    }

    subprocess.run(
        [
            sys.executable,
            str(INSTALL_SCRIPT),
            "--target",
            "both",
            "--write-env-from-current",
        ],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    codex_skill = codex_home / "skills" / "lexmount-browser"
    claude_skill = home / ".claude" / "skills" / "lexmount-browser"
    for installed in (codex_skill, claude_skill):
        assert (installed / "SKILL.md").exists()
        assert (installed / "scripts" / "lexmount-browser").exists()
        assert 'LEXMOUNT_API_KEY="key"' in (installed / ".env").read_text(
            encoding="utf-8"
        )


def test_install_script_rejects_newlines_in_env_values(tmp_path: Path) -> None:
    env = {
        **os.environ,
        "CODEX_HOME": str(tmp_path / "codex-home"),
        "LEXMOUNT_API_KEY": "key\nLEXMOUNT_BASE_URL=https://attacker.test",
        "LEXMOUNT_PROJECT_ID": "project",
    }

    completed = subprocess.run(
        [
            sys.executable,
            str(INSTALL_SCRIPT),
            "--target",
            "codex",
            "--write-env-from-current",
        ],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "contains a newline" in completed.stderr


def test_installed_wrapper_loads_skill_env_and_delegates_to_runtime(
    tmp_path: Path,
) -> None:
    codex_home = tmp_path / "codex-home"
    api_key = r"key#from\"skill"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_runtime = fake_bin / "lex-browser-runtime"
    fake_runtime.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import json, os, sys",
                "print(json.dumps({",
                "  'argv': sys.argv[1:],",
                "  'api_key': os.environ.get('LEXMOUNT_API_KEY'),",
                "  'project_id': os.environ.get('LEXMOUNT_PROJECT_ID'),",
                "}))",
            ]
        ),
        encoding="utf-8",
    )
    fake_runtime.chmod(0o755)

    install_env = {
        **os.environ,
        "CODEX_HOME": str(codex_home),
        "LEXMOUNT_API_KEY": api_key,
        "LEXMOUNT_PROJECT_ID": "project-from-skill-env",
    }
    subprocess.run(
        [
            sys.executable,
            str(INSTALL_SCRIPT),
            "--target",
            "codex",
            "--write-env-from-current",
        ],
        check=True,
        env=install_env,
        capture_output=True,
        text=True,
    )

    run_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"LEXMOUNT_API_KEY", "LEXMOUNT_PROJECT_ID"}
    }
    run_env.update(
        {
            "CODEX_HOME": str(codex_home),
            "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "LEX_BROWSER_RUNTIME_NO_BOOTSTRAP": "1",
        }
    )
    wrapper = (
        codex_home / "skills" / "lexmount-browser" / "scripts" / "lexmount-browser"
    )

    completed = subprocess.run(
        [str(wrapper), "session", "create"],
        check=True,
        env=run_env,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload == {
        "argv": ["session", "create"],
        "api_key": api_key,
        "project_id": "project-from-skill-env",
    }
