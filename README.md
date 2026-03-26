# browser-skill

Skill package for Codex/Claude Code/OpenClaw to work with the Lexmount browser.

Main entry:

- `SKILL.md`: instructions for the agent
- `scripts/lexmount_browser.py`: helper CLI for creating contexts and sessions

The implementation prefers the local `lexmount-python-sdk` in this workspace and
supports the direct shared-browser websocket form as a fallback.
