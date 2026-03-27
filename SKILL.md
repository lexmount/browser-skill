---
name: lexmount-browser
description: Use when the user wants Codex to create, reuse, or connect to a Lexmount remote browser session. Supports creating contexts, creating browser sessions, returning CDP websocket URLs, listing contexts, and closing sessions. Prefer this skill over hand-written curl requests when working with Lexmount browser automation.
compatibility: "Requires Python 3 plus the dependencies in `requirements.txt`. Use the installed skill path under `~/.codex/skills/lexmount-browser` by default. If running from this repository during development, prefer `lexmount-python-sdk-quickstart/venv` because it already has `httpx` and `python-dotenv`. Authenticated SDK commands require `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID`. `LEXMOUNT_BASE_URL` is optional and should be set to `https://apitest.local.lexmount.net` only in the office test environment."
allowed-tools: Bash
---

# Lexmount Browser

Use this skill when the task needs a Lexmount remote browser for automation, debugging, or manual connection setup.

## Setup check

Initialize an installed skill with a virtual environment:

```bash
python3 -m venv ~/.codex/skills/lexmount-browser/.venv
~/.codex/skills/lexmount-browser/.venv/bin/pip install -r ~/.codex/skills/lexmount-browser/requirements.txt
```

Then use:

```bash
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py --help
```

If you do not want a virtual environment, you can also use:

```bash
python3 ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py --help
```

If you are developing from this repository instead of the installed skill, prefer:

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py --help
```

Use any Python environment that can import `httpx` and `dotenv`.

## Environment

Environment variables:

- `LEXMOUNT_API_KEY`
- `LEXMOUNT_PROJECT_ID`
- `LEXMOUNT_BASE_URL`

- `LEXMOUNT_BASE_URL` is optional.

Do not set `LEXMOUNT_BASE_URL` when using production credentials.

Only set it for the office test environment:

- `LEXMOUNT_BASE_URL=https://apitest.local.lexmount.net`

## When to use this skill

- The user wants Codex to create or reuse a Lexmount browser context.
- The user wants a CDP websocket URL for Playwright or another browser client.
- The user wants the SDK path instead of manually constructing HTTP requests.
- The user wants the quick direct websocket path and accepts the shared-browser limitation.

## When not to use this skill

- The task only needs raw HTTP calls unrelated to browser sessions.
- The user is asking for Kubernetes deployment or browser-manager server work rather than browser session usage.

## Quick start

Run the installed helper:

```bash
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare
```

This returns JSON with:

- `context_id`
- `session_id`
- `connect_url`
- `inspect_url`

## Preferred workflow

1. Prefer the installed helper script instead of hand-writing HTTP requests.
2. `prepare` does not create a context by default.
3. Pass `--create-context` only when the user explicitly needs a new persistent browser profile.
4. Pass `--context-id` when the user wants to reuse an existing context.
5. Use `close-session --session-id <id>` when cleanup is needed.
6. Only use `direct-url` when the user explicitly wants the quick shared-browser connection method from `wss://.../connection`.

## Commands

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare --create-context`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare --context-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py list-contexts`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py close-session --session-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py direct-url`

## Behavior rules

- Prefer `prepare` over `direct-url`.
- Default session browser mode is `normal`.
- Default context mode is `read_write`.
- `prepare` creates a plain session by default and does not allocate a context unless `--create-context` or `--context-id` is provided.
- Return structured JSON to the caller instead of prose when using the helper script.
- If the SDK import fails, tell the user that `lexmount-python-sdk` or its Python dependencies are not ready in the current environment.
- If credentials are missing, report which environment variable is absent.

## Validation note

For local validation, prefer exporting credentials in the current shell for one command instead of hard-coding them into the skill files or script.

If the provided `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID` are production credentials, do not add `LEXMOUNT_BASE_URL`.

## Implementation note

The helper script can read credentials from the installed skill `.env` file at `~/.codex/skills/lexmount-browser/.env`.

When working inside this monorepo, the repository copy of the script also injects the local SDK source tree from `lexmount-python-sdk/src` into `PYTHONPATH`, so a separate package install is not required there.
