# browser-skill

Skill package for Codex/Claude Code/OpenClaw to work with the Lexmount browser.

Main entry:

- `SKILL.md`: instructions for the agent
- `scripts/lexmount_browser.py`: helper CLI for creating contexts and sessions

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
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare
```

Other common commands:

```bash
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare --create-context
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py prepare --context-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py list-contexts
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py close-session --session-id <id>
~/.codex/skills/lexmount-browser/.venv/bin/python ~/.codex/skills/lexmount-browser/scripts/lexmount_browser.py direct-url
```

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
