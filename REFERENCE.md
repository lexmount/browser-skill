# Lexmount Browser Reference

## Connection modes

### 1. Direct shared websocket

Use when the user explicitly wants the fast path and accepts a shared browser instance.

Format:

```text
wss://api.lexmount.cn/connection?project_id=<project_id>&api_key=<api_key>
```

If `LEXMOUNT_BASE_URL` points to another host, the helper derives the websocket base from it.

### 2. SDK-based session

Preferred mode.

Flow:

1. Create a plain session by default
2. Only create or reuse a context when persistence is explicitly needed
3. Read `connect_url` from the returned session object
4. Connect with Playwright `chromium.connect_over_cdp(connect_url)`

## Helper commands

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py prepare
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py prepare --create-context
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py list-contexts
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py close-session --session-id <id>
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py direct-url
```

## Expected JSON fields

### `prepare`

- `context_id`
- `created_context`
- `session_id`
- `connect_url`
- `inspect_url`
- `container_id`

### `list-contexts`

- `count`
- `contexts`

### `close-session`

- `session_id`
- `closed`

### `direct-url`

- `connect_url`

## Environment

- `LEXMOUNT_API_KEY`
- `LEXMOUNT_PROJECT_ID`
- `LEXMOUNT_BASE_URL`

`LEXMOUNT_BASE_URL` is optional. Do not set it for production credentials.

Only use it for the office test environment:

```bash
export LEXMOUNT_BASE_URL=https://apitest.local.lexmount.net
```
