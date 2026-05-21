---
name: notion-doc-reader
description: Use when a user provides Notion page links and asks to read page content, recursively read child pages, or verify Notion API access using official Notion API endpoints. This skill is read-only by default and portable across repositories.
---

# Notion Doc Reader

Read Notion page content through official Notion API endpoints. This skill is
portable: copying this directory to another repository preserves the workflow,
scripts, and tests.

## Scope

Use this skill for:

- Reading a user-provided Notion page as markdown.
- Recursively reading direct child pages.
- Verifying that a local Notion internal integration token can read a page.
- Producing a compact page tree summary for agent context.

Do not use this skill for:

- Deleting, trashing, archiving, erasing, or moving Notion content.
- Updating Notion pages unless a separate write-oriented workflow is designed.
- Replacing official Notion API / SDK surfaces with a custom runtime client.

## Requirements

- `NOTION_ACCESS_TOKEN` in the environment or in a local `.env`.
- Optional `NOTION_VERSION`; defaults to `2026-03-11`.
- The Notion integration must have `Read content`.
- The target page or a parent page must be shared with the integration.

## Read Workflow

1. Load token from local environment or `.env`.
2. Extract the page id from the user-provided Notion URL.
3. Read page markdown with:
   `GET /v1/pages/{page_id}/markdown`.
4. List page children with:
   `GET /v1/blocks/{page_id}/children?page_size=100`.
5. For every direct `child_page` block, repeat the same read flow until
   `--max-depth` or `--max-pages` is reached.

Default traversal follows page hierarchy only. It does not deep-scan every
non-page nested block because large pages can contain many nested blocks and
make smoke tests slow or noisy. `--max-pages` defaults to `50` to avoid
accidentally crawling a very wide workspace tree.

## Smoke Command

```bash
python3 .ai/skills/notion-doc-reader/scripts/notion_read_smoke.py \
  --env-file /path/to/.env \
  --max-depth 3 \
  --max-pages 50 \
  "<notion-page-url>"
```

Output is JSON with page ids, titles, markdown character counts, Notion
markdown truncation flags, optional `truncated_at_page_limit` page-limit flags,
unknown block ids, and discovered child pages. The script does not print tokens
or full page markdown.

## Verification

Run the bundled unit tests:

```bash
python3 .ai/skills/notion-doc-reader/scripts/test_notion_read_smoke.py
```

Run live read-only smoke only when a token and user-approved Notion page links
are available:

```bash
python3 .ai/skills/notion-doc-reader/scripts/notion_read_smoke.py \
  --env-file /path/to/.env \
  --max-depth 3 \
  --max-pages 50 \
  "<notion-page-url-1>" \
  "<notion-page-url-2>"
```
