---
name: lexmount-browser
description: Use when the user wants Codex to create, reuse, inspect, or operate a Lexmount remote browser session. Supports context and session lifecycle commands plus Playwright-backed action commands such as opening pages, clicking, typing, screenshots, waiting for selectors, and extracting page snapshots. Prefer this skill over hand-written curl requests or ad hoc Playwright scripts when working with Lexmount browser automation.
compatibility: "Requires Python 3 plus the dependencies in `requirements.txt`, including `lexmount` and `playwright` for installed-skill usage. Use the installed skill path under `~/.codex/skills/lexmount-browser` by default. If running from this repository during development, prefer `lexmount-python-sdk-quickstart/venv` because it already has the SDK dependencies. Authenticated SDK commands require `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID`. `LEXMOUNT_BASE_URL` is optional and should be set to `https://apitest.local.lexmount.net` only in the office test environment."
allowed-tools: Bash
---

# Lexmount Browser

Use this skill when the task needs a Lexmount remote browser for automation, debugging, or manual connection setup.

## Setup check

During installation, the installer asks whether you are using `browser.lexmount.cn` or `browser.lexmount.com`.
If `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID` already exist in the current shell, the installer can import them directly into the installed skill.

API Keys pages:

- `https://browser.lexmount.cn/settings/api-keys`
- `https://browser.lexmount.com/settings/api-keys`

During `npx` installation, prefer confirming the prompt that creates the skill-local virtual environment and installs dependencies.

If that step was skipped, initialize the installed skill manually:

The virtual environment should live inside the installed skill directory at `~/.codex/skills/lexmount-browser/.venv`.

```bash
python3 -m venv ~/.codex/skills/lexmount-browser/.venv
~/.codex/skills/lexmount-browser/.venv/bin/pip install -r ~/.codex/skills/lexmount-browser/requirements.txt
```

This installs the Lexmount SDK and the Playwright Python client into the skill-local virtual environment.

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

Use any Python environment that can import `lexmount`, `playwright`, `httpx`, and `dotenv`.

## Environment

Environment variables:

- `LEXMOUNT_API_KEY`
- `LEXMOUNT_PROJECT_ID`
- `LEXMOUNT_BASE_URL`

- `LEXMOUNT_BASE_URL` is optional.

- If you use `browser.lexmount.com`, set `LEXMOUNT_BASE_URL=https://api.lexmount.com`.
- If you use `browser.lexmount.cn`, do not set `LEXMOUNT_BASE_URL`.

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

1. Prefer the installed helper script instead of hand-writing HTTP requests or ad hoc Playwright code.
2. Use `session create` for lifecycle work and `action ...` commands for browser interactions.
3. `prepare` remains available as a compatibility alias for `session create`.
4. `session create` does not create a context by default.
5. Pass `--create-context` only when the user explicitly needs a new persistent browser profile.
6. Pass `--context-id` when the user wants to reuse an existing context.
7. Use `session close --session-id <id>` when cleanup is needed.
8. Use `action open-url`, `action click`, `action type`, `action wait-selector`, `action screenshot`, `action eval`, or `action snapshot` for the common interaction path.
9. Use `case validate` and `case run` when the task is a repeatable multi-step flow that should live in a file instead of a one-off terminal command.
10. Use `run submit/list/summary/watch/retry` when the user wants to launch the same case multiple times, inspect batch-level status, quickly understand local run results, or rerun failed batches.
11. Only use `direct-url` when the user explicitly wants the quick shared-browser connection method from `wss://.../connection`.
12. Use `research knowledge` when the task is knowledge gathering from search engines with one producer browser generating links and multiple consumer browsers capturing page content in parallel.

## Commands

### Session lifecycle

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create --create-context`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create --context-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session list`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session get --session-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session close --session-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session keepalive --session-id <id>`

### Context lifecycle

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context create`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context list`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context get --context-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context delete --context-id <id>`

### Browser actions

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action open-url --session-id <id> --url https://example.com`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action wait-selector --session-id <id> --selector 'button'`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action click --session-id <id> --selector 'button'`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action type --session-id <id> --selector 'input[name=q]' --text 'hello'`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action screenshot --session-id <id> --output /tmp/example.png`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action eval --session-id <id> --expression '() => document.title'`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action snapshot --session-id <id>`

### Case execution

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py case validate --file /path/to/case.json`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py case run --file /path/to/case.json --stop-on-error`

### Batch run control

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run submit --file /path/to/case.json --count 5 --concurrency 2`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run list`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run summary --batch-id <batch_id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run watch --batch-id <batch_id> --expected-count 5`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run watch --batch-id <batch_id> --live --changes-only`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run retry --batch-id <batch_id>`

### Research templates

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py research knowledge --query "browser automation" --max-links 100 --consumer-count 6`
- `research knowledge` creates one producer browser for search result pages and multiple consumer browsers that stream-capture result page content into a local run directory.

### Compatibility and direct connection

- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py list-contexts`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py close-session --session-id <id>`
- `~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py direct-url`

## Behavior rules

- Prefer `session create` over `direct-url`.
- Default session browser mode is `normal`.
- Default context mode is `read_write`.
- `session create` creates a plain session by default and does not allocate a context unless `--create-context` or `--context-id` is provided.
- Return structured JSON to the caller instead of prose when using the helper script.
- If the SDK import fails, tell the user that `lexmount-python-sdk` or its Python dependencies are not ready in the current environment.
- If credentials are missing, report which environment variable is absent.
- If session creation hits the platform parallel browser/session limit, return a structured `browser_parallel_limit_reached` error and make the message explicit that the browser parallel quota is full.

## Validation note

For local validation, prefer exporting credentials in the current shell for one command instead of hard-coding them into the skill files or script.

If the provided `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID` are production credentials, do not add `LEXMOUNT_BASE_URL`.

## Implementation note

The helper script can read credentials from the installed skill `.env` file at `~/.codex/skills/lexmount-browser/.env`.

When working inside this monorepo, the repository copy of the script also injects the local SDK source tree from `lexmount-python-sdk/src` into `PYTHONPATH`, so a separate package install is not required there.
