# browser-skill

Skill package for Codex/Claude Code/OpenClaw to work with the Lexmount browser.

Main entry:

- `SKILL.md`: instructions for the agent
- `scripts/lexmount_browser.py`: helper CLI for session/context lifecycle plus basic browser actions

The implementation prefers the local `lexmount-python-sdk` in this workspace and
supports the direct shared-browser websocket form as a fallback.

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

- one producer browser opens search result pages and keeps enqueueing links
- multiple consumer browsers pull links from the queue in parallel
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
- `--consumer-count`: number of consumer browsers
- `--search-engine`: built-in defaults for `bing`, `google`, or `duckduckgo`
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

If this folder is later published as an npm package, the installer entrypoint can
be invoked with:

```bash
npx @lexmount/browser-skill-installer
```

## Publish path

To make the install experience look like a one-line CLI install:

1. Publish this folder as the npm package `@lexmount/browser-skill-installer`
2. Ensure the package contains `SKILL.md`, `REFERENCE.md`, `scripts/`, and `tools/install-skill.mjs`
3. Users run:

```bash
npx @lexmount/browser-skill-installer
```

The installer copies the skill into:

```text
~/.codex/skills/lexmount-browser
```

## COS publish

To build the npm tarball and upload it to the public COS bucket:

```bash
npm install
node tools/upload-package-to-cos.mjs
```

Default target:

- bucket: `npm-1377899528`
- region: `ap-nanjing`
- prefix: `packages/`

The script uploads both a versioned tarball and a `latest` tarball, then prints
the public URL that can be used with `npx`.
