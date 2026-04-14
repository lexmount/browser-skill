# browser-skill

Skill package for Codex/Claude Code/OpenClaw to work with the Lexmount browser.

Main entry:

- `SKILL.md`: instructions for the agent
- `scripts/lexmount_browser.py`: helper CLI for session/context lifecycle plus basic browser actions

The implementation prefers the local `lexmount-python-sdk` in this workspace and
supports the direct shared-browser websocket form as a fallback.

If session creation hits the platform's active browser/session cap, the helper
returns a structured JSON error with a dedicated `browser_parallel_limit_reached`
error code, an explicit Chinese message that the browser parallel quota is full,
and the original SDK `status_code` plus `response` for debugging.

## Installation flow

Run:

```bash
npx @lexmount/browser-skill-installer
```

The installer now:

- asks you to choose `browser.lexmount.cn` or `browser.lexmount.com`
- checks whether the current shell already has `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID`
- if existing values are found, asks whether to import them into the installed skill
- shows the matching API Keys page before falling back to manual entry

API Keys pages:

- `browser.lexmount.cn`: `https://browser.lexmount.cn/settings/api-keys`
- `browser.lexmount.com`: `https://browser.lexmount.com/settings/api-keys`

Environment output rules:

- both environments write `LEXMOUNT_API_KEY` and `LEXMOUNT_PROJECT_ID`
- `browser.lexmount.com` also writes `LEXMOUNT_BASE_URL=https://api.lexmount.com`
- `browser.lexmount.cn` does not write `LEXMOUNT_BASE_URL`

## Runtime commands

During `npx` installation, the installer can create the skill-local virtual environment for you.

If you skip that step, initialize it manually after installation:

Create the virtual environment inside the installed skill directory at `~/.codex/skills/lexmount-browser/.venv`.

```bash
python3 -m venv ~/.codex/skills/lexmount-browser/.venv
~/.codex/skills/lexmount-browser/.venv/bin/pip install -r ~/.codex/skills/lexmount-browser/requirements.txt
```

This installs the Lexmount SDK and the Playwright Python client into the skill-local virtual environment.

After installation into `~/.codex/skills/lexmount-browser`, use:

```bash
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create
```

Other common commands:

```bash
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create --create-context
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session create --context-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session list
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session get --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py session close --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context create
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py context list
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action open-url --session-id <id> --url https://example.com
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action click --session-id <id> --selector 'button'
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py action screenshot --session-id <id> --output /tmp/example.png
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py case validate --file /path/to/case.json
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py case run --file /path/to/case.json --stop-on-error
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run submit --file /path/to/case.json --count 5 --concurrency 2
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run list
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run summary --batch-id <batch_id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py run retry --batch-id <batch_id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py direct-url
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py research knowledge --query "browser use benchmark" --max-links 100 --consumer-count 8
```

Bundled example cases:

- `browser-skill/examples/basic-open.json`: smoke case for open, wait, snapshot, and screenshot
- `browser-skill/examples/retry-demo.json`: success case for retry demonstrations after a failing batch is fixed
- `browser-skill/examples/retry-demo-fail.json`: intentionally failing case for retry workflow validation

## Streaming knowledge research template

The `research knowledge` command turns the skill into a producer/consumer browser pipeline:

- producer and consumer browser sessions are created in parallel at startup
- producer and consumer browser sessions are also closed in parallel during cleanup
- one producer browser opens search result pages and keeps enqueueing links
- multiple consumer browsers pull links from the queue in parallel
- each consumer processes every URL in a fresh page to avoid cross-site navigation interference
- each consumer stores `page.json` artifacts with title, URL, HTML excerpt, and text excerpt
- optional screenshots can be captured with `--screenshot`
- producer-side search page failures are recorded and skipped instead of aborting the whole run
- producer-side search navigation now tries current-DOM recovery first and then retries once with a longer timeout

Example:

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py \
  research knowledge \
  --query "site:openai.com browser agents" \
  --max-links 100 \
  --consumer-count 6 \
  --search-engine bing \
  --output-dir /tmp/lexmount-runs/research-openai
```

Important parameters:

- `--query`: the search query issued by the producer browser
- `--max-links`: how many search result links to stream to consumers
- `--min-success-pages`: keep producing beyond `--max-links` until this many pages succeed, unless search pages are exhausted
- `--consumer-count`: number of consumer browsers
- `--producer-mode`: producer browser mode, default `normal`, optional `light`
- `--browser-mode`: consumer browser mode, default `normal`, optional `light`
- `--search-engine`: built-in defaults for `bing`, `google`, `baidu`, or `duckduckgo`
- `--fallback-search-engines`: comma-separated fallback engines; default is `baidu`, so producer starts with Bing and falls back when needed
- `--search-url-template`: optional custom search URL template using `{query}`, `{offset}`, and `{page}`
- `--result-selector`: optional CSS selector for result links
- `--keep-sessions`: keep sessions open instead of closing them automatically

Output files inside the run directory:

- `events.jsonl`: producer and consumer lifecycle events
- `links.jsonl`: links emitted by the producer
- `results.jsonl`: per-link success or failure records from consumers
- `summary.json`: full structured summary for the run
- `pages/<rank>-.../page.html`: raw HTML saved for each successful page
- `pages/<rank>-.../page.json`: captured page artifact per consumed URL

For repository-local development, you can still use the quickstart virtualenv:

```bash
lexmount-python-sdk-quickstart/venv/bin/python browser-skill/scripts/lexmount_browser.py prepare
```

## Install shape

For local development, install into Codex by linking or copying this folder into:

- `~/.codex/skills/lexmount-browser`

The npm package installer entrypoint can be invoked with:

```bash
npx @lexmount/browser-skill-installer
```

## Publish path

This package is published as:

- npm package: `@lexmount/browser-skill-installer`

The published package contains `SKILL.md`, `REFERENCE.md`, `scripts/`, and `tools/install-skill.mjs`.

Users run:

```bash
npx @lexmount/browser-skill-installer
```

The installer copies the skill into:

```text
~/.codex/skills/lexmount-browser
```

## npm release workflow

The npm publish flow matches the Lexmount JS SDK release pattern:

1. bump `package.json` to a new unpublished version
2. push the commit and tag
3. create and publish a GitHub Release
4. GitHub Actions workflow `publish.yml` validates the package and publishes it to npm via trusted publishing

Local validation entrypoint:

```bash
npm run release:npm:check
```
