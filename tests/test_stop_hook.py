from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STOP_HOOK = ROOT / ".claude" / "hooks" / "stop.sh"


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.DEVNULL)


def _write_active_plan(path: Path, body: str, name: str = "plan.md") -> Path:
    plan_dir = path / ".ai" / "superpowers" / "plans" / "active"
    plan_dir.mkdir(parents=True)
    plan_path = plan_dir / name
    plan_path.write_text(body)
    return plan_path


def _write_large_untracked_change(path: Path) -> None:
    (path / "large-change.txt").write_text("\n".join(f"line {i}" for i in range(40)))


def test_stop_hook_blocks_when_validation_parser_fails(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    plan_path = _write_active_plan(
        tmp_path,
        "# Plan\n\n- [x] Implemented\n\n## Validation\n\n- `pytest` passed\n",
    )
    _write_large_untracked_change(tmp_path)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-" ] && [ "$2" = "$PLAN_PATH" ]; then\n'
        '  touch "$PARSER_SENTINEL"\n'
        "  exit 1\n"
        "fi\n"
        f'exec "{sys.executable}" "$@"\n'
    )
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CC_STOP_MAX": "100",
            "PATH": f"{fake_bin}:{env['PATH']}",
            "PLAN_PATH": str(plan_path),
            "PARSER_SENTINEL": str(tmp_path / "parser-called"),
        }
    )

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=tmp_path,
        input='{"session_id":"session-1","stop_hook_active":false}',
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    assert '"decision": "block"' in result.stdout
    assert "Validation" in result.stdout
    assert (tmp_path / "parser-called").exists()


def test_stop_hook_blocks_when_validation_section_is_empty(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_active_plan(tmp_path, "# Plan\n\n- [x] Implemented\n\n## Validation\n")
    _write_large_untracked_change(tmp_path)

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=tmp_path,
        input='{"session_id":"session-empty-validation","stop_hook_active":false}',
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CC_STOP_MAX": "100",
        },
        check=False,
    )

    assert result.returncode == 0
    assert '"decision": "block"' in result.stdout
    assert "Validation" in result.stdout


def test_stop_hook_handles_quote_heavy_plan_path(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_active_plan(
        tmp_path,
        "# Plan\n\n- [x] Implemented\n",
        name='plan-""".md',
    )
    _write_large_untracked_change(tmp_path)

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=tmp_path,
        input='{"session_id":"session-quote-path","stop_hook_active":false}',
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CC_STOP_MAX": "100",
        },
        check=False,
    )

    assert result.returncode == 0
    assert '"decision": "block"' in result.stdout
    assert "Validation" in result.stdout


def test_stop_hook_does_not_eval_session_id(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=tmp_path,
        input=(
            '{"session_id":"x; touch ' + str(marker) + '; #","stop_hook_active":false}'
        ),
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(tmp_path / "home")},
        check=False,
    )

    assert result.returncode == 0
    assert not marker.exists()


def test_stop_hook_does_not_traverse_task_directory(tmp_path: Path) -> None:
    home = tmp_path / "home"
    escaped_tasks = home / "escape"
    escaped_tasks.mkdir(parents=True)
    (escaped_tasks / "task.json").write_text('{"status":"pending"}')

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=tmp_path,
        input='{"session_id":"../../escape","stop_hook_active":false}',
        text=True,
        capture_output=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )

    assert result.returncode == 0
    assert '"decision": "block"' not in result.stdout


def test_stop_hook_max_zero_disables_hook(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_active_plan(tmp_path, "# Plan\n\n- [x] Implemented\n\n## Validation\n")
    _write_large_untracked_change(tmp_path)

    result = subprocess.run(
        ["bash", str(STOP_HOOK)],
        cwd=tmp_path,
        input='{"session_id":"session-disabled","stop_hook_active":false}',
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "CC_STOP_MAX": "0",
        },
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
