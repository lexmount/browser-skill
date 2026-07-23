---
name: lexmount-browser
description: Use when the user asks for web research, search, recommendations, comparison, evidence gathering, website inspection, browser automation, page interaction, form filling, login-gated browsing, screenshots, scraping/extraction, or operating a remote browser with Lexmount Browser.
allowed-tools: Bash
---

# Lexmount Browser

Use this skill when a task needs Lexmount browser capability from an installed
Claude Code or Codex skill.

The skill is intentionally thin: it delegates implementation to
`lex-browser-runtime` so lifecycle, browser actions, case execution, error
normalization, and future runtime abilities live in one package instead of being
duplicated inside the skill.

## Default Trigger Scope

Use this skill by default for research and browser automation tasks, even when
the user does not explicitly say "Lexmount", unless the user asks not to use a
remote browser or the task can be answered better without opening a browser.

## Research Preset Routing

Use `research ... --preset gov-policy` when the task asks about local policy,
regional policy, official policy evidence, government portals, government
websites,政务服务, 政府官网, 政府门户, 官方政策, 地方政策, 各地政策,
城市政策, 区县政策, 补贴政策, 人才政策, 购房补贴, 社保, 医保, 公积金,
or business-environment policy. Use `--preset food` for restaurant/local food
recommendations. Use `--preset web` for general web research that is not better
served by a specialized preset.

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
  --concurrency 5
```

Use plain `research run` without observer only when the user explicitly asks for
no UI, only artifacts, or a non-interactive run.

One-time prelogin for login-walled custom research sources:

```bash
"$SKILL_DIR/scripts/prelogin-auth-contexts" --sources <source-id>
```

The script opens Lexmount browser windows for manual login and saves source
contexts to `~/.lex-browser-runtime/auth-contexts.json`. Future `research run`
commands load that file automatically and reuse matching source contexts in
`read_write` mode so normal Codex research prompts do not need extra flags.

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
   `LEX_BROWSER_OBSERVER_URL`, and run research without `--keep-sessions` so
   completed browser windows are released and removed from the observer page.
   For `--preset food`, omit `--max-sites` by default so all 13 login-free food
   sources run. Login-walled sources such as Xiaohongshu, Zhihu, Douyin, Amap,
   and Weibo are intentionally excluded from the default food preset.
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
   `--concurrency 5`, and no `--keep-sessions` unless the user explicitly wants
   to keep completed sessions for debugging.
4. Read the returned `summary.json`, `sources.jsonl`, and `events.jsonl`.
5. Summarize the answer from the extracted evidence. Mention which sources
   succeeded or failed when it changes confidence.

Research artifacts:

- `routes.json`: deterministic source jobs and URLs.
- `events.jsonl`: start/finish timeline for each source job.
- `sources.jsonl`: one compact evidence record per source.
- `summary.json`: aggregate status, output paths, jobs, and extracted results.

Auth contexts:

- Run `"$SKILL_DIR/scripts/prelogin-auth-contexts"` once when a custom source
  blocks useful results behind login.
- The saved file is local user state at
  `~/.lex-browser-runtime/auth-contexts.json` by default.
- `research run` automatically uses matching saved contexts by source id.
- Use `--auth-contexts-file <path>` only to override the default file, or
  `--no-auth-contexts` to force anonymous research.
- Saved contexts are used with `read_write` mode by default because the current
  Lexmount session API rejects `read_only` context reuse.

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
  --concurrency 5
```

The observer page shows only live browser inspect windows and run activity.
Completed sessions are closed and removed from the page. After the run, read
`summary.json`, `sources.jsonl`, and `events.jsonl`, then write the final answer
from the extracted evidence. Use `--keep-sessions` only for debugging.

## Command Map

Session/context lifecycle:

```bash
"$SKILL_DIR/scripts/lexmount-browser" session create
"$SKILL_DIR/scripts/lexmount-browser" session create --enable-downloads
"$SKILL_DIR/scripts/lexmount-browser" session create --enable-recording
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
"$SKILL_DIR/scripts/prelogin-auth-contexts" --sources <source-id>
"$SKILL_DIR/scripts/lexmount-browser" research route --query "最好吃的红烧肉" --preset food
"$SKILL_DIR/scripts/lexmount-browser" research run --query "最好吃的红烧肉" --preset food --max-sites 13 --concurrency 5
"$SKILL_DIR/scripts/lexmount-browser" research run --query "best browser automation news" --preset web --max-sites 2
"$SKILL_DIR/scripts/lexmount-browser" research route --query "深圳 人才补贴政策" --preset gov-policy
"$SKILL_DIR/scripts/lexmount-browser" research run --query "杭州 购房补贴政策" --preset gov-policy --max-sites 8
```

Use `--preset gov-policy` for local government policy research. It routes
queries through a curated packaged list of 36 major city official government
portals and opens those portal home pages directly. The package intentionally
excludes the former 2736 province/city/county all-portal records and the
non-major-city records from the original 366 city list. The runtime operates
the portal page's visible search UI when one can be found; the packaged data
does not assume every portal has a fixed search page URL. It does not fallback
to external `site:` search. Runtime routing caps `gov-policy` at the available
major-city portal count and 12 concurrent browser sessions.

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
