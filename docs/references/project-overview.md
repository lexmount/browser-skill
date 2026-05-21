# Lex Browser Runtime Project Overview

> This file is the stable source of truth for the current project boundary,
> architecture, commands, dependency rules, and integration facts.

## System Goal

`lex-browser-runtime` provides a Python SDK layer between browser agents and
Lexmount-managed browsers. This repository is now the canonical `browser-skill`
home for both that runtime package and the installable Lexmount browser skill.
The first milestone extracts runtime-assist capabilities from the browser-use
experiment into a reusable package while preserving benchmark gains.

## System Boundaries

- Inputs: browser session requests, task URLs, adapter JSON, site-hint YAML, and
  runtime action requests from an upper-layer agent.
- Core processing: create/connect/close browser sessions, match runtime
  capabilities, and record runtime telemetry.
- Outputs: browser session descriptors, matched capability summaries, and
  benchmark-friendly runtime traces.
- External systems: Lexmount browser service, Chrome DevTools Protocol endpoints,
  and benchmark harnesses such as `browseruse-bench-staging`.
- Non-targets: LLM planning, full task execution, HTTP service, MCP server, or
  agent-specific UI automation policies in the first SDK milestone.

## Layering

### Browser Layer

Owns browser lifecycle contracts and backend implementations.

- `LexmountBackend`: creates and stops Lexmount sessions through the Lexmount SDK.
- `ExistingCdpBackend`: wraps a caller-provided CDP URL for tests and migration
  shims.
- `LexmountBrowserAdmin`: exposes the reusable `browser-skill` lifecycle surface
  for session/context list/get/create/close, direct websocket URL generation, and
  stable Lexmount SDK error normalization.

### CLI / Skill Surface

The command-line entrypoint is a thin wrapper over the runtime package, not a
second implementation. It currently covers the reusable base of
`lexmount/browser-skill`: session lifecycle, context lifecycle, and direct
shared websocket URL generation, plus primitive Playwright actions (`open-url`,
`wait-selector`, `click`, `type`, `screenshot`, `eval`, `snapshot`) and single
case validate/run.

The installable Claude Code / Codex skill lives in `skills/lexmount-browser`.
Its scripts delegate to `lex-browser-runtime` and only own installation,
credential loading, and stable command discovery. Batch retry/watch and research
producer/consumer flows should land as separate runtime changes before being
exposed through the skill.

The skill is distributed through the npm package
`@lexmount/browser-skill-installer`. The package copies
`skills/lexmount-browser` into Codex and/or Claude Code skill directories, writes
a skill-local `.env` when credentials are provided, and can bootstrap the
skill-local runtime virtual environment.

### Registry Layer

Loads and matches runtime knowledge.

- Adapter JSON files describe known site endpoints and strategy metadata.
- Site-hint YAML files describe operating notes and runtime strategies.
- Matching returns structured capabilities; prompt text is a rendering choice for
  an upper-layer agent, not the source of truth.

### Runtime Facade

Provides a small SDK surface for callers.

- Create/close browser sessions.
- Match capabilities for a task or URL.
- Record runtime action traces.

### Telemetry Layer

Produces serializable metadata for benchmark output. The intended consumer is
`result.json.agent_metadata.runtime_assist`.

## Runtime Commands

```bash
make venv
make deps
make check
uv run lex-browser-runtime --help
python3 scripts/install_lexmount_browser_skill.py --target codex
npm run release:npm:check
```

Equivalent low-level commands:

```bash
uv venv --python python3.11 .venv
uv pip install --python .venv/bin/python -e . --group dev
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy .
```

## Project Dependency Rules

- Python 3.11+ is required to match the browser-use benchmark environment.
- Runtime dependencies live in `pyproject.toml`.
- The Lexmount SDK remains an optional runtime import in the backend module. Unit
  tests must mock it instead of requiring live credentials.
- Real credentials must stay in `.env` or the execution environment.

## Current Core Runtime Areas

- `lex_browser_runtime/browser/`: browser session models and backend contracts.
- `lex_browser_runtime/registry/`: adapter and site-hint loading/matching.
- `lex_browser_runtime/telemetry.py`: runtime trace models.
- `lex_browser_runtime/runtime.py`: public SDK facade.
- `tests/`: unit tests for the SDK boundary.

## Integration Plan

1. SDK core PR in this repository.
2. Browser-use integration PR that replaces direct adapter/site-hint loading with
   this SDK.
3. Same-20 LexBench-Browser parity run in `browseruse-bench-staging`.

## Communication Defaults

- Default discussion language: Chinese.
- Code identifiers, commands, and third-party terms remain English.
