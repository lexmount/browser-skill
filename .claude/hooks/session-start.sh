#!/usr/bin/env bash
# SessionStart hook: print AI-first collaboration context for Claude Code.
# This hook only informs; it never blocks.
set -e

cat <<'EOF'
[AI-first collaboration context]

Truth sources:
  .ai/skills/ai-collaboration-workflow/SKILL.md
  docs/references/project-overview.md

Quick reminders:
  - Use skills before responding when applicable.
  - Non-trivial work needs a local plan under .ai/superpowers/plans/active/.
  - Completion claims need fresh verification evidence.
  - Keep shared rules tool-neutral in the workflow skill; agent-specific details live in agent entry files.
  - Keep one truth source for each rule.

Local artifacts:
  .ai/topics/<slug>/                    long-lived topics
  .ai/superpowers/plans/active/<slug>.md local active plans
  .ai/feedback/<slug>/round<N>.md        user feedback input
  .ai/skills/                            shared skills source

EOF

python3 <<'PY'
import sys
from pathlib import Path

plan_dir = Path(".ai/superpowers/plans/active")
if not plan_dir.is_dir():
    sys.exit(0)

plans = sorted(
    path
    for path in plan_dir.glob("*.md")
    if path.name != "README.md"
)
if plans:
    print("[active plans]")
    for path in plans:
        print(f"  - {path}")
PY
