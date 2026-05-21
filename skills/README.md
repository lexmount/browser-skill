# Optional Skills

This directory is reserved for optional skills that ship with the template but are not installed by default.

Default-installed reusable skills live in `.ai/skills/` and are exposed to local agents through `.claude/skills` and `.codex/skills` symlinks. Optional skills may stay here until a project decides to promote them into `.ai/skills/`.

The portable workflow skill itself (`.ai/skills/ai-collaboration-workflow/`) is designed to be publishable as a standalone unit; its install contract lives in its `SKILL.md`.

## Available Skills

| Skill | Purpose |
|-------|---------|
| `lexmount-browser` | Installable Claude Code / Codex skill that delegates Lexmount browser work to `lex-browser-runtime`. |

## Install

To install `lexmount-browser` into local Codex and Claude Code skill directories:

```bash
python3 scripts/install_lexmount_browser_skill.py --target both
```

To install manually, copy the skill into the target agent:

```bash
cp -R skills/lexmount-browser ~/.codex/skills/lexmount-browser
cp -R skills/lexmount-browser ~/.claude/skills/lexmount-browser
```

After installing, start a new agent session or reload available skills so the
agent can discover the copied skill.

## Update

To update an installed optional skill from this template:

```bash
rm -rf .ai/skills/<skill-name>
cp -R skills/<skill-name> .ai/skills/<skill-name>
```

Review local project customizations before replacing an installed skill.
