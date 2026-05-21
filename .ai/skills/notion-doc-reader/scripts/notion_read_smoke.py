"""Read-only smoke harness for official Notion API document access.

This script is bundled inside the notion-doc-reader skill so the skill can be
copied to another repository and used without repo-specific code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen


UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?"
    r"[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}"
)


class NotionReadAPI(Protocol):
    """Read-only subset of official Notion API endpoints used by this skill."""

    def get_page(self, page_id: str) -> dict[str, Any]:
        """Return page metadata from `GET /v1/pages/{page_id}`."""

    def get_page_markdown(self, page_id: str) -> dict[str, Any]:
        """Return markdown from `GET /v1/pages/{page_id}/markdown`."""

    def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        """Return all children from `GET /v1/blocks/{block_id}/children`."""


class OfficialNotionAPI:
    """Thin read-only caller for official Notion API endpoints."""

    def __init__(self, token: str, version: str) -> None:
        if not token:
            raise ValueError("NOTION_ACCESS_TOKEN must not be empty")
        self._token = token
        self._version = version

    def get_page(self, page_id: str) -> dict[str, Any]:
        """Return page metadata from the official Notion API."""

        page_id = normalize_page_id(page_id)
        return self._get(f"/v1/pages/{page_id}")

    def get_page_markdown(self, page_id: str) -> dict[str, Any]:
        """Return page markdown from the official Notion API."""

        page_id = normalize_page_id(page_id)
        return self._get(f"/v1/pages/{page_id}/markdown")

    def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        """Return all direct child blocks for a Notion block or page."""

        block_id = normalize_page_id(block_id)
        children: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            query = {"page_size": "100"}
            if cursor is not None:
                query["start_cursor"] = cursor
            response = self._get(f"/v1/blocks/{block_id}/children?{urlencode(query)}")
            results = response.get("results")
            if not isinstance(results, list):
                raise RuntimeError(f"Unexpected children response for {block_id}")
            children.extend(block for block in results if isinstance(block, dict))
            if response.get("has_more") is not True:
                return children
            next_cursor = response.get("next_cursor")
            if not isinstance(next_cursor, str):
                raise RuntimeError(f"Missing pagination cursor for {block_id}")
            cursor = next_cursor

    def _get(self, path: str) -> dict[str, Any]:
        request = Request(
            f"https://api.notion.com{path}",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Notion-Version": self._version,
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GET {path} failed with HTTP {error.code}: {body}"
            ) from error
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise RuntimeError(f"GET {path} returned non-object JSON")
        return decoded


def load_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding existing environment."""

    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), clean_env_value(value))


def clean_env_value(value: str) -> str:
    """Return a simple dotenv value with optional wrapping quotes removed."""

    stripped = value.strip()
    if stripped.startswith(("'", '"')):
        quote = stripped[0]
        end = stripped.find(quote, 1)
        if end != -1:
            remainder = stripped[end + 1 :].strip()
            if remainder and not remainder.startswith("#"):
                raise ValueError("Trailing characters after closing quote")
            return stripped[1:end]
    if " #" in stripped:
        stripped = stripped.split(" #", 1)[0].rstrip()
    return strip_wrapping_quotes(stripped)


def strip_wrapping_quotes(value: str) -> str:
    """Remove one matching pair of surrounding single or double quotes."""

    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        return stripped[1:-1]
    return stripped


def parse_page_id(reference: str) -> str:
    """Extract and normalize a Notion page id from a URL or raw id."""

    parts = urlsplit(reference)
    query = parse_qs(parts.query)
    candidates = [value for value in query.get("p", []) if value]
    candidates.extend([parts.path, reference])

    for candidate in candidates:
        match = UUID_RE.search(candidate)
        if match is not None:
            return normalize_page_id(match.group(0))
    raise ValueError(f"No Notion page id found in {reference!r}")


def normalize_page_id(page_id: str) -> str:
    """Validate and normalize a raw Notion page id."""

    match = UUID_RE.fullmatch(page_id)
    if match is None:
        raise ValueError(f"Invalid Notion page id {page_id!r}")
    compact = match.group(0).replace("-", "").lower()
    return (
        f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-"
        f"{compact[16:20]}-{compact[20:32]}"
    )


def crawl(
    reference: str, *, api: NotionReadAPI, max_depth: int, max_pages: int
) -> list[dict[str, Any]]:
    """Read a page and recursively read direct child pages."""

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    root_id = parse_page_id(reference)
    queue = [{"id": root_id, "title": _page_title(api.get_page(root_id)), "depth": 0}]
    seen: set[str] = set()
    pages: list[dict[str, Any]] = []

    while queue and len(pages) < max_pages:
        item = queue.pop(0)
        page_id = item["id"]
        if page_id in seen:
            continue
        seen.add(page_id)

        markdown = api.get_page_markdown(page_id)
        if markdown.get("object") != "page_markdown":
            raise RuntimeError(f"Unexpected markdown response for {page_id}")

        child_pages = _direct_child_pages(api.list_block_children(page_id))
        pages.append(
            {
                "id": page_id,
                "title": item["title"],
                "depth": item["depth"],
                "markdown_chars": len(markdown.get("markdown") or ""),
                "truncated": markdown.get("truncated"),
                "unknown_block_ids": markdown.get("unknown_block_ids", []),
                "child_pages": child_pages,
            }
        )
        if item["depth"] >= max_depth:
            continue
        for child in child_pages:
            queue.append(
                {
                    "id": child["id"],
                    "title": child["title"],
                    "depth": item["depth"] + 1,
                }
            )
    if queue and pages:
        pages[-1]["truncated_at_page_limit"] = True
    return pages


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser."""

    parser = argparse.ArgumentParser(
        description="Read-only Notion recursive page smoke test."
    )
    parser.add_argument("references", nargs="+", help="Notion page URLs or ids")
    parser.add_argument("--env-file", default=".env", help="Path to local .env")
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--max-pages", type=int, default=50)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the read-only Notion smoke harness."""

    parser = build_parser()
    args = parser.parse_args(argv)
    load_env(Path(args.env_file))

    token = os.environ.get("NOTION_ACCESS_TOKEN")
    if token is None:
        raise RuntimeError("NOTION_ACCESS_TOKEN is not set")
    version = os.environ.get("NOTION_VERSION", "2026-03-11")
    api = OfficialNotionAPI(token=token, version=version)

    result = {
        reference: crawl(
            reference,
            api=api,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
        )
        for reference in args.references
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _page_title(page: dict[str, Any]) -> str:
    properties = page.get("properties", {})
    if not isinstance(properties, dict):
        return ""
    for value in properties.values():
        if isinstance(value, dict) and value.get("type") == "title":
            title = value.get("title", [])
            if isinstance(title, list):
                return "".join(
                    item.get("plain_text", "")
                    for item in title
                    if isinstance(item, dict)
                )
    return ""


def _direct_child_pages(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    child_pages: list[dict[str, str]] = []
    for block in blocks:
        if block.get("type") != "child_page":
            continue
        block_id = block.get("id")
        child_page = block.get("child_page", {})
        if not isinstance(block_id, str) or not isinstance(child_page, dict):
            continue
        try:
            block_id = normalize_page_id(block_id)
        except ValueError:
            continue
        title = child_page.get("title", "")
        child_pages.append(
            {"id": block_id, "title": title if isinstance(title, str) else ""}
        )
    return child_pages


if __name__ == "__main__":
    raise SystemExit(main())
