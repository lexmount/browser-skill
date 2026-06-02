---
name: lexmount-browser
description: Use when the user wants Claude Code or Codex to create, reuse, inspect, or operate a Lexmount remote browser through lex-browser-runtime, including multi-source browser research when the user asks to use Lexmount Browser. Provides a stable installed-skill wrapper for session/context lifecycle, direct-url, primitive browser actions, browser case validation/run, and research route/run without hand-written curl or ad hoc Playwright scripts.
allowed-tools: Bash
---

# Lexmount Browser

Use this skill when a task needs Lexmount browser capability from an installed
Claude Code or Codex skill.

The skill is intentionally thin: it delegates implementation to
`lex-browser-runtime` so lifecycle, browser actions, case execution, error
normalization, and future runtime abilities live in one package instead of being
duplicated inside the skill.

## First Check

Resolve the installed skill directory:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/lexmount-browser"
[ -d "$SKILL_DIR" ] || SKILL_DIR="$HOME/.claude/skills/lexmount-browser"
```

Then use the wrapper:

```bash
"$SKILL_DIR/scripts/lexmount-browser" --help
```

The wrapper loads `$SKILL_DIR/.env` when present, auto-bootstraps
`$SKILL_DIR/.venv` when needed, and then invokes the `lex-browser-runtime` CLI.

## Required Configuration

Set credentials in the shell or in `$SKILL_DIR/.env`:

```bash
LEXMOUNT_API_KEY=...
LEXMOUNT_PROJECT_ID=...
```

Region rules:

- China/default region: leave `LEXMOUNT_BASE_URL` unset.
- Global region: set `LEXMOUNT_BASE_URL=https://api.lexmount.com`.
- Office test environment only: set
  `LEXMOUNT_BASE_URL=https://apitest.local.lexmount.net`.

Never print or persist live API keys. `direct-url` masks URL credentials by
default; use `--reveal-url` only for an immediate interactive connection.

## Quick Start

Create a session:

```bash
"$SKILL_DIR/scripts/lexmount-browser" session create
```

Open a page and capture compact state:

```bash
"$SKILL_DIR/scripts/lexmount-browser" action open-url --session-id <id> --url https://example.com
"$SKILL_DIR/scripts/lexmount-browser" action snapshot --session-id <id> --max-chars 2000
```

Close the session when finished:

```bash
"$SKILL_DIR/scripts/lexmount-browser" session close --session-id <id>
```

Run a repeatable case:

```bash
"$SKILL_DIR/scripts/lexmount-browser" case validate --file "$SKILL_DIR/examples/basic-open.json"
"$SKILL_DIR/scripts/lexmount-browser" case run --file "$SKILL_DIR/examples/basic-open.json" --stop-on-error --close-created-session
```

Run multi-source browser research through the observer UI by default:

```bash
"$SKILL_DIR/scripts/lexmount-browser" observer serve --host 127.0.0.1 --port 8765
LEX_BROWSER_OBSERVER_URL=http://127.0.0.1:8765 \
"$SKILL_DIR/scripts/lexmount-browser" research run \
  --query "最好吃的红烧肉" \
  --preset food \
  --max-sites 5 \
  --concurrency 5 \
  --keep-sessions
```

Use plain `research run` without observer only when the user explicitly asks for
no UI, only artifacts, or a non-interactive run.

## Preferred Workflow

1. Use this skill before writing raw Lexmount SDK snippets, curl calls, or
   one-off Playwright scripts.
2. Prefer `session create` over `direct-url` for real browser work.
3. Use `action ...` commands for one-off browser operations.
4. Use `case validate` and `case run` when the flow has multiple deterministic
   browser steps or should be reproducible.
5. For recommendation, comparison, or evidence-gathering tasks where the user
   asks to use Lexmount Browser, default to the observer research workflow:
   start `observer serve`, open or report `http://127.0.0.1:8765`, set
   `LEX_BROWSER_OBSERVER_URL`, and run research with kept sessions.
6. Skip the observer only when the user explicitly asks for no UI, only
   artifacts, or a non-interactive run.
7. Return or summarize the CLI JSON payloads instead of translating them into
   vague prose.
8. If credentials are missing, tell the user exactly which environment variable
   is absent.
9. If session creation hits a parallel limit, surface the structured
   `browser_parallel_limit_reached` error and suggest closing existing sessions.

## Research Workflow

For a query such as `找最好吃的红烧肉，用 Lexmount Browser 完成`, keep Claude
Code or Codex as the planner and final summarizer. Use the runtime only for
routing, concurrent browser execution, extraction, and artifact generation.

Default research behavior: when the user says to use the `lexmount-browser`
skill for research, search, recommendation, or comparison, trigger the local
observer frontend by default. The expected first visible effect is the observer
page at `http://127.0.0.1:8765`, followed by browser cards appearing as
`browser_created` events arrive.

Recommended flow:

1. Start `observer serve --host 127.0.0.1 --port 8765` unless it is already
   running.
2. Open or report `http://127.0.0.1:8765` so the user can watch the run.
3. Run `research run` with `LEX_BROWSER_OBSERVER_URL=http://127.0.0.1:8765`,
   `--concurrency 5`, and `--keep-sessions` unless the user or environment
   calls for different limits.
4. Read the returned `summary.json`, `sources.jsonl`, and `events.jsonl`.
5. Summarize the answer from the extracted evidence. Mention which sources
   succeeded or failed when it changes confidence.

Research artifacts:

- `routes.json`: deterministic source jobs and URLs.
- `events.jsonl`: start/finish timeline for each source job.
- `sources.jsonl`: one compact evidence record per source.
- `summary.json`: aggregate status, output paths, jobs, and extracted results.

## Observer Research Workflow

Use this workflow by default for research prompts. It gives the user a local
page showing each concurrent Lexmount browser window while Codex or Claude Code
still writes the final answer.

Start the observer in one shell:

```bash
"$SKILL_DIR/scripts/lexmount-browser" observer serve --host 127.0.0.1 --port 8765
```

Then run research with the observer URL:

```bash
LEX_BROWSER_OBSERVER_URL=http://127.0.0.1:8765 \
"$SKILL_DIR/scripts/lexmount-browser" research run \
  --query "最好吃的红烧肉" \
  --preset food \
  --max-sites 5 \
  --concurrency 5 \
  --keep-sessions
```

The observer page shows browser inspect windows and run activity. After the run,
read `summary.json`, `sources.jsonl`, and `events.jsonl`, then write the final
answer from the extracted evidence. Close kept sessions when the demo is done.

## Command Map

Session/context lifecycle:

```bash
"$SKILL_DIR/scripts/lexmount-browser" session create
"$SKILL_DIR/scripts/lexmount-browser" session create --create-context
"$SKILL_DIR/scripts/lexmount-browser" session create --context-id <context_id>
"$SKILL_DIR/scripts/lexmount-browser" session list --status active
"$SKILL_DIR/scripts/lexmount-browser" session get --session-id <id>
"$SKILL_DIR/scripts/lexmount-browser" session keepalive --session-id <id> --duration 10
"$SKILL_DIR/scripts/lexmount-browser" session close --session-id <id>
"$SKILL_DIR/scripts/lexmount-browser" context list
"$SKILL_DIR/scripts/lexmount-browser" context create
"$SKILL_DIR/scripts/lexmount-browser" context get --context-id <id>
"$SKILL_DIR/scripts/lexmount-browser" context delete --context-id <id>
```

Browser actions:

```bash
"$SKILL_DIR/scripts/lexmount-browser" action open-url --session-id <id> --url https://example.com
"$SKILL_DIR/scripts/lexmount-browser" action wait-selector --session-id <id> --selector 'body'
"$SKILL_DIR/scripts/lexmount-browser" action click --session-id <id> --selector 'button'
"$SKILL_DIR/scripts/lexmount-browser" action type --session-id <id> --selector 'input[name=q]' --text 'hello'
"$SKILL_DIR/scripts/lexmount-browser" action screenshot --session-id <id> --output /tmp/lexmount.png
"$SKILL_DIR/scripts/lexmount-browser" action eval --session-id <id> --expression '() => document.title'
"$SKILL_DIR/scripts/lexmount-browser" action snapshot --session-id <id>
```

Case files:

```bash
"$SKILL_DIR/scripts/lexmount-browser" case validate --file /path/to/case.json
"$SKILL_DIR/scripts/lexmount-browser" case run --file /path/to/case.json --stop-on-error --close-created-session
```

Research:

```bash
"$SKILL_DIR/scripts/lexmount-browser" observer serve --host 127.0.0.1 --port 8765
"$SKILL_DIR/scripts/lexmount-browser" research route --query "最好吃的红烧肉" --preset food
"$SKILL_DIR/scripts/lexmount-browser" research run --query "最好吃的红烧肉" --preset food --max-sites 10 --concurrency 5
"$SKILL_DIR/scripts/lexmount-browser" research run --query "best browser automation news" --preset web --max-sites 2
```

Compatibility aliases:

```bash
"$SKILL_DIR/scripts/lexmount-browser" prepare
"$SKILL_DIR/scripts/lexmount-browser" list-contexts
"$SKILL_DIR/scripts/lexmount-browser" close-session --session-id <id>
"$SKILL_DIR/scripts/lexmount-browser" direct-url
```

## Current Boundary

This migrated skill covers the core `browser-skill` path:
session/context lifecycle, direct URL generation, primitive Playwright-backed
actions, single case validate/run, and multi-source research route/run.

Batch retry/watch and full producer/consumer orchestration templates are
intentionally not part of this installed skill yet. Use separate runtime PRs for
those so the runtime layer stays reviewable.
