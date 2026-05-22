# lex-browser-runtime in browser-skill

`lex-browser-runtime` is the SDK-first runtime layer for Lexmount-backed browser
automation.

This repository is the canonical home for both the runtime package and the
installable Lexmount browser skill. The earlier `lex-browser-runtime` repository
was used to extract and validate the runtime layer; release and skill
distribution now happen from `lexmount/browser-skill`.

The current milestone keeps the transport deliberately small while moving the
runtime assist capabilities out of browser-use: browser lifecycle, capability
registry, telemetry contracts, API fetch safety, response compaction, compact
state detection, and deterministic high-volume completion contracts live here.
The near-term acceptance test is parity: browser-use should be able to call this
SDK and rerun the same LexBench-Browser 20-case slice with the same
runtime-assist gains.

The runtime is also the home for the reusable engine behind the
`lexmount/browser-skill` surface. Agent-facing skills and installers should call
this package instead of owning their own Lexmount lifecycle/action implementation.

## Scope

- Create, describe, and close Lexmount browser sessions.
- List/get/close sessions and contexts for skill/CLI workflows.
- Support an existing-CDP backend for local tests and integration shims.
- Expose a small JSON CLI for Lexmount session/context lifecycle and direct
  shared websocket URLs.
- Run Playwright-backed primitive browser actions against an explicit CDP URL,
  Lexmount session id, or direct shared websocket URL.
- Validate and run browser-skill case files with JSONL events and summary
  artifacts.
- Route and run multi-source browser research jobs with concurrent Lexmount
  sessions and structured evidence artifacts for an outer agent to summarize.
- Load runtime capability knowledge from adapter JSON and site-hint YAML files.
- Fetch adapter-approved public APIs with pre/post redirect URL safety checks.
- Compact known API/page responses into stable, answerable runtime observations.
- Provide deterministic runtime completion contracts for high-volume flows where
  UI clicking is the wrong primitive.
- Produce agent-agnostic runtime traces that benchmark harnesses can store under
  `agent_metadata.runtime_assist`.

## Non-Goals

- This package is not an agent planner.
- This package still does not expose an HTTP or MCP service; callers use the SDK
  directly or the thin local CLI.
- The first SDK milestone does not integrate Skyvern, Agent-TARS, Claude Code, or
  OpenAI CUA.
- Batch retry/watch and full producer/consumer orchestration templates from
  `browser-skill` are intentionally kept out of this extraction and should move
  in separate PRs.

## CLI Surface

Install the optional skill dependencies when using the CLI against Lexmount
browsers:

```bash
uv pip install -e '.[skill]'
```

Common commands:

```bash
lex-browser-runtime session create
lex-browser-runtime session create --create-context --metadata-json '{"owner":"demo"}'
lex-browser-runtime session list --status active
lex-browser-runtime session get --session-id <id>
lex-browser-runtime session close --session-id <id>
lex-browser-runtime context list
lex-browser-runtime direct-url
lex-browser-runtime action open-url --session-id <id> --url https://example.com
lex-browser-runtime action snapshot --session-id <id>
lex-browser-runtime case validate --file examples/basic-open.json
lex-browser-runtime case run --file examples/basic-open.json --stop-on-error
lex-browser-runtime research route --query "最好吃的红烧肉" --preset food
lex-browser-runtime research run --query "最好吃的红烧肉" --preset food --max-sites 10 --concurrency 5
```

The CLI emits structured JSON compatible with the original browser skill helper,
including the dedicated `browser_parallel_limit_reached` error code when the
Lexmount active browser quota is full.

`direct-url` returns a masked Lexmount shared-browser websocket URL by default
because the underlying protocol carries the API key in the URL query string. Use
`--reveal-url` only when an interactive caller needs the live URL, and treat that
output as a secret: do not store it in persistent logs, issue trackers, or shared
transcripts.

## Development

```bash
make venv
make deps
make check
```

The package supports Python 3.11+ so it can be installed into the existing
browser-use benchmark environment.

## Installable Agent Skill

The portable Claude Code / Codex skill lives in
`skills/lexmount-browser`. It is a thin wrapper around this package, so installed
agents can quickly use Lexmount without copying the old `browser-skill` helper
implementation.

Install into both local Codex and Claude Code skill directories:

```bash
python3 scripts/install_lexmount_browser_skill.py --target both
```

Optionally write the current Lexmount credentials into the installed skill and
bootstrap its local runtime environment:

```bash
LEXMOUNT_API_KEY=... LEXMOUNT_PROJECT_ID=... \
python3 scripts/install_lexmount_browser_skill.py \
  --target both \
  --write-env-from-current \
  --bootstrap
```

After installation, agents should call the stable wrapper:

```bash
~/.codex/skills/lexmount-browser/scripts/lexmount-browser session create
~/.codex/skills/lexmount-browser/scripts/lexmount-browser action snapshot --session-id <id>
~/.codex/skills/lexmount-browser/scripts/lexmount-browser case run --file ~/.codex/skills/lexmount-browser/examples/basic-open.json --close-created-session
~/.codex/skills/lexmount-browser/scripts/lexmount-browser research run --query "最好吃的红烧肉" --preset food --max-sites 10 --concurrency 5
```

For Claude Code, use the same path under `~/.claude/skills/lexmount-browser`.

For research or recommendation tasks, the installed skill should not become a
second LLM agent. Claude Code or Codex remains responsible for query
interpretation, source selection adjustments, and the final answer. The runtime
runner handles deterministic routing, concurrent Lexmount browser sessions, page
extraction, and artifact writing. A run returns paths for `routes.json`,
`events.jsonl`, `sources.jsonl`, and `summary.json`.

## npm Installer Release

The installable skill is packaged as:

- npm package: `@lexmount/browser-skill-installer`
- binary: `lexmount-browser-skill-install`

After publishing, users can install without cloning this repository:

```bash
npx @lexmount/browser-skill-installer
```

Non-interactive installation is available for CI or scripted setup:

```bash
LEXMOUNT_INSTALL_NONINTERACTIVE=1 \
LEXMOUNT_INSTALL_TARGET=both \
LEXMOUNT_INSTALL_REGION=china \
LEXMOUNT_INSTALL_DEPS=1 \
LEXMOUNT_API_KEY=... \
LEXMOUNT_PROJECT_ID=... \
npx @lexmount/browser-skill-installer
```

Release flow:

1. Bump `package.json` to a new unpublished version.
2. Push the change and tag.
3. Create a GitHub Release for the tag.
4. `.github/workflows/publish.yml` validates the package and runs
   `npm publish`.

Local release validation:

```bash
npm run release:npm:check
```
