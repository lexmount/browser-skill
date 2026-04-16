# Lexmount Browser Reference

## Connection modes

### 1. Direct shared websocket

Use when the user explicitly wants the fast path and accepts a shared browser instance.

This mode still connects to a specific region endpoint. For the default China region
preset, the direct websocket format is:

Format:

```text
wss://api.lexmount.cn/connection?project_id=<project_id>&api_key=<api_key>
```

If `LEXMOUNT_BASE_URL` points to another region endpoint, the helper derives the websocket base from it automatically.

### 2. SDK-based session

Preferred mode.

Flow:

1. Create a plain session by default
2. Only create or reuse a context when persistence is explicitly needed
3. Read `connect_url` from the returned session object
4. Connect with Playwright `chromium.connect_over_cdp(connect_url)`

## Helper commands

Installed skill initialization:

During `npx` installation, prefer confirming the prompt that creates the skill-local virtual environment and installs dependencies.

If that step was skipped, run:

Create the virtual environment inside the installed skill directory at `~/.codex/skills/lexmount-browser/.venv`.

```bash
python3 -m venv ~/.codex/skills/lexmount-browser/.venv
~/.codex/skills/lexmount-browser/.venv/bin/pip install -r ~/.codex/skills/lexmount-browser/requirements.txt
```

This installs the Lexmount SDK and the Playwright Python client into the skill-local virtual environment.

```bash
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create --create-context
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create --context-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session list
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session get --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session close --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session keepalive --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context create
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context list
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context get --context-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context delete --context-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action open-url --session-id <id> --url https://example.com
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action wait-selector --session-id <id> --selector 'button'
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action click --session-id <id> --selector 'button'
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action type --session-id <id> --selector 'input[name=q]' --text 'hello'
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action screenshot --session-id <id> --output /tmp/example.png
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action eval --session-id <id> --expression '() => document.title'
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action snapshot --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py case validate --file /path/to/case.json
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py case run --file /path/to/case.json --stop-on-error
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run submit --file /path/to/case.json --count 5 --concurrency 2
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run list
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run summary --batch-id <batch_id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run watch --batch-id <batch_id> --expected-count 5
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run watch --batch-id <batch_id> --live --changes-only
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run retry --batch-id <batch_id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py direct-url
```

## Case file shape

`case run` and `case validate` accept a JSON or YAML object shaped like:

```json
{
  "session": {
    "create": true,
    "browser_mode": "normal",
    "create_context": false
  },
  "steps": [
    { "action": "open-url", "url": "https://example.com" },
    { "action": "wait-selector", "selector": "body" },
    { "action": "snapshot", "max_chars": 2000 }
  ]
}
```

Target selection can be provided in one of four ways:

1. `session.create = true`
2. `target.session_id = "..."`
3. `target.connect_url = "..."`
4. `target.direct_url = true`

Bundled examples:

1. `browser-skill/examples/basic-open.json`
2. `browser-skill/examples/retry-demo.json`
3. `browser-skill/examples/retry-demo-fail.json`

## Local run registry

`run submit` stores batch artifacts under:

```text
/tmp/lexmount-runs/<batch_id>/
  batch-summary.json
  run-001/summary.json
  run-002/summary.json
  ...
```

It also appends one line per batch to:

```text
/tmp/lexmount-runs/index.jsonl
```

For repository-local development, the equivalent commands can still use:

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py ...
```

## Expected JSON fields

### `session create` / `prepare`

- `context_id`
- `created_context`
- `session`
  - `session_id`
  - `connect_url`
  - `inspect_url`
  - `container_id`
  - `status`
  - `browser_mode`

### `session list`

- `count`
- `status_filter`
- `sessions`
- `pagination`

### `session get`

- `session`

### `session close`

- `session_id`
- `closed`

### `session keepalive`

- `session_id`
- `checks`
- `final_status`
- `snapshots`

### `context list` / `list-contexts`

- `count`
- `contexts`

### `context create` / `context get`

- `context`

### `context delete`

- `context_id`
- `deleted`

### `action open-url`

- `result.url`
- `result.title`
- `result.status`

### `action wait-selector`

- `result.selector`
- `result.state`
- `result.text`

### `action click`

- `result.clicked`
- `result.selector`

### `action type`

- `result.typed`
- `result.press_enter`

### `action screenshot`

- `result.path`
- `result.full_page`

### `action eval`

- `result.expression`
- `result.value`

### `action snapshot`

- `result.url`
- `result.title`
- `result.html`
- `result.text`

### `case validate`

- `file`
- `valid`
- `errors`
- `step_count`

### `case run`

- `file`
- `run_id`
- `artifacts_dir`
- `session`
- `steps`

### `run submit`

- `batch_id`
- `batch_dir`
- `count`
- `ok_count`
- `failed_count`
- `runs`

### `run list`

- `count`
- `runs`
- `runs_root`

### `run summary`

- `batch_id`
- `batch_dir`
- `count`
- `ok_count`
- `failed_count`

### `run watch`

- `checks`
- `latest`
- `snapshots`
- `latest.runs`
  Each run reports `status`, `current_step`, `last_event_type`, and any captured `failure`
- With `--live`, the command prints compact human-readable snapshots instead of JSON
- With `--changes-only`, `--live` prints only when the rendered state changes

### `run retry`

- `source_batch_id`
- `batch_id`
- `batch_dir`
- `retried_runs`
- `ok_count`
- `failed_count`

### `direct-url`

- `connect_url`

## Region Configuration

- `LEXMOUNT_API_KEY`
- `LEXMOUNT_PROJECT_ID`
- `LEXMOUNT_BASE_URL`

`LEXMOUNT_BASE_URL` is optional.

- If you use the `Global region` endpoint, set `LEXMOUNT_BASE_URL=https://api.lexmount.com`.
- If you use the `China region` endpoint, do not set `LEXMOUNT_BASE_URL`.

Only use it for the office test environment:

```bash
export LEXMOUNT_BASE_URL=https://apitest.local.lexmount.net
```

The installed skill also reads `~/.codex/skills/lexmount-browser/.env` when present.
