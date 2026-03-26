---
name: lexmount-browser
description: Use when the user wants Codex to create, reuse, or connect to a Lexmount remote browser session, especially through the local Lexmount Python SDK in this workspace. Supports creating contexts, creating browser sessions, returning CDP websocket URLs, listing contexts, and closing sessions. Prefer this skill over hand-written curl requests when working with Lexmount browser automation.
compatibility: "Requires Python 3. Prefer the existing virtual environment at `lexmount-python-sdk-quickstart/venv` because it already has `httpx` and `python-dotenv`. Authenticated SDK commands require `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID`. `LEXMOUNT_BASE_URL` is optional and should be set to `https://apitest.local.lexmount.net` in the office test environment."
allowed-tools: Bash
---

# Lexmount Browser

Use this skill when the task needs a Lexmount remote browser for automation, debugging, or manual connection setup.

## Setup check

Prefer the existing quickstart virtual environment in this repository:

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py --help
```

If that environment is unavailable, use any Python environment that can import `httpx` and `dotenv`.

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

Run the helper from the workspace root:

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py prepare
```

This returns JSON with:

- `context_id`
- `session_id`
- `connect_url`
- `inspect_url`

## Preferred workflow

1. Prefer the local SDK path in this repository instead of hand-writing HTTP requests.
2. Use `prepare` to create a context when the user needs an isolated persistent browser profile.
3. Pass `--context-id` when the user wants to reuse an existing context.
4. Use `close-session --session-id <id>` when cleanup is needed.
5. Only use `direct-url` when the user explicitly wants the quick shared-browser connection method from `wss://.../connection`.

## Commands

- `lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py prepare`
- `lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py prepare --context-id <id>`
- `lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py list-contexts`
- `lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py close-session --session-id <id>`
- `lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py direct-url`

## Behavior rules

- Prefer `prepare` over `direct-url`.
- Default session browser mode is `normal`.
- Default context mode is `read_write`.
- Return structured JSON to the caller instead of prose when using the helper script.
- If the SDK import fails, tell the user that `lexmount-python-sdk` or its Python dependencies are not ready in the current environment.
- If credentials are missing, report which environment variable is absent.

## Validation note

For local validation, prefer exporting credentials in the current shell for one command instead of hard-coding them into the skill files or script.

If the provided `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID` are production credentials, do not add `LEXMOUNT_BASE_URL`.

## Implementation note

The helper script injects the local SDK source tree from `lexmount-python-sdk/src` into `PYTHONPATH`, so a separate package install is not required when working inside this monorepo.
