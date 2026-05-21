#!/usr/bin/env bash
# UserPromptSubmit hook: print the most recently touched active plan.
# This hook only informs; it never blocks.
set -e

python3 <<'PY'
from pathlib import Path

plan_dir = Path(".ai/superpowers/plans/active")
if not plan_dir.is_dir():
    print("[no active plan] For non-trivial work, use writing-plans and save the plan to .ai/superpowers/plans/active/<slug>.md.")
    raise SystemExit

plans = [
    path
    for path in plan_dir.glob("*.md")
    if path.name != "README.md"
]
if not plans:
    print("[no active plan] For non-trivial work, use writing-plans and save the plan to .ai/superpowers/plans/active/<slug>.md.")
    raise SystemExit

latest = max(plans, key=lambda path: path.stat().st_mtime)
print(f"[active plan] {latest.stem}")
PY
