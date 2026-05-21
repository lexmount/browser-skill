"""Unit tests for the notion-doc-reader smoke harness."""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "notion_read_smoke.py"
ROOT_ID = "260e7e99-8fb2-80a6-8196-e6d32306c3d5"
CHILD_ID = "295e7e99-8fb2-80e8-9fd5-e48695b79523"
GRANDCHILD_ID = "2d2e7e99-8fb2-800b-be61-d65fcc4b5351"


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("notion_read_smoke", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Notion read smoke script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeNotionAPI:
    def get_page(self, page_id: str):
        return {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": f"title:{page_id}"}],
                }
            }
        }

    def get_page_markdown(self, page_id: str):
        return {
            "object": "page_markdown",
            "id": page_id,
            "markdown": f"# {page_id}",
            "truncated": False,
            "unknown_block_ids": [],
        }

    def list_block_children(self, block_id: str):
        if block_id == ROOT_ID:
            return [
                {
                    "id": CHILD_ID,
                    "type": "child_page",
                    "child_page": {"title": "Child A"},
                },
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "has_children": True,
                },
            ]
        if block_id == CHILD_ID:
            return [
                {
                    "id": GRANDCHILD_ID,
                    "type": "child_page",
                    "child_page": {"title": "Grandchild A"},
                }
            ]
        return []


class NullMarkdownAPI(FakeNotionAPI):
    def get_page_markdown(self, page_id: str):
        return {
            "object": "page_markdown",
            "id": page_id,
            "markdown": None,
            "truncated": False,
            "unknown_block_ids": [],
        }


class WideTreeAPI(FakeNotionAPI):
    def list_block_children(self, block_id: str):
        if block_id == ROOT_ID:
            return [
                {
                    "id": CHILD_ID,
                    "type": "child_page",
                    "child_page": {"title": "Child A"},
                },
                {
                    "id": GRANDCHILD_ID,
                    "type": "child_page",
                    "child_page": {"title": "Child B"},
                },
            ]
        return []


class PaginatedOfficialAPI:
    def __init__(self):
        smoke = load_smoke_module()
        self._api = smoke.OfficialNotionAPI(token="token", version="2026-03-11")
        self._api._get = self._get
        self.paths = []

    def list_block_children(self, block_id: str):
        return self._api.list_block_children(block_id)

    def _get(self, path: str):
        self.paths.append(path)
        if "start_cursor=cursor-2" in path:
            return {
                "results": [{"id": "paragraph-2", "type": "paragraph"}],
                "has_more": False,
            }
        return {
            "results": [{"id": "paragraph-1", "type": "paragraph"}],
            "has_more": True,
            "next_cursor": "cursor-2",
        }


class NotionReadSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_notion_access_token = os.environ.pop("NOTION_ACCESS_TOKEN", None)

    def tearDown(self) -> None:
        os.environ.pop("NOTION_ACCESS_TOKEN", None)
        if self._original_notion_access_token is not None:
            os.environ["NOTION_ACCESS_TOKEN"] = self._original_notion_access_token

    def test_load_env_strips_wrapping_quotes(self) -> None:
        smoke = load_smoke_module()
        with tempfile.NamedTemporaryFile("w", delete=False) as env_file:
            env_file.write('NOTION_ACCESS_TOKEN="secret-token"\n')
            env_path = Path(env_file.name)

        try:
            smoke.load_env(env_path)
        finally:
            env_path.unlink()

        self.assertEqual(os.environ["NOTION_ACCESS_TOKEN"], "secret-token")

    def test_clean_env_value_strips_unquoted_inline_comment(self) -> None:
        smoke = load_smoke_module()

        self.assertEqual(smoke.clean_env_value("secret-token # local"), "secret-token")
        self.assertEqual(
            smoke.clean_env_value('"secret-token # literal"'),
            "secret-token # literal",
        )

    def test_clean_env_value_strips_quotes_before_inline_comment(self) -> None:
        smoke = load_smoke_module()

        self.assertEqual(
            smoke.clean_env_value('"secret-token" # local'),
            "secret-token",
        )

    def test_clean_env_value_rejects_trailing_text_after_quote(self) -> None:
        smoke = load_smoke_module()

        with self.assertRaisesRegex(ValueError, "Trailing characters"):
            smoke.clean_env_value('"secret-token"x')

    def test_parse_page_id_from_notion_url(self) -> None:
        smoke = load_smoke_module()

        page_id = smoke.parse_page_id(
            "https://www.notion.so/workspace/Browser-Use-"
            "2d2e7e998fb2800bbe61d65fcc4b5351"
        )

        self.assertEqual(page_id, "2d2e7e99-8fb2-800b-be61-d65fcc4b5351")

    def test_parse_page_id_prefers_subpage_query_param(self) -> None:
        smoke = load_smoke_module()

        page_id = smoke.parse_page_id(
            "https://www.notion.so/workspace/Parent-"
            "260e7e998fb280a68196e6d32306c3d5"
            "?p=2d2e7e998fb2800bbe61d65fcc4b5351&pm=c"
        )

        self.assertEqual(page_id, "2d2e7e99-8fb2-800b-be61-d65fcc4b5351")

    def test_crawl_follows_child_page_blocks_only_by_default(self) -> None:
        smoke = load_smoke_module()

        pages = smoke.crawl(ROOT_ID, api=FakeNotionAPI(), max_depth=2, max_pages=50)

        self.assertEqual(
            [(page["id"], page["title"], page["depth"]) for page in pages],
            [
                (ROOT_ID, f"title:{ROOT_ID}", 0),
                (CHILD_ID, "Child A", 1),
                (GRANDCHILD_ID, "Grandchild A", 2),
            ],
        )
        self.assertEqual(pages[0]["child_pages"][0]["id"], CHILD_ID)

    def test_crawl_reports_zero_chars_for_null_markdown(self) -> None:
        smoke = load_smoke_module()

        pages = smoke.crawl(ROOT_ID, api=NullMarkdownAPI(), max_depth=0, max_pages=50)

        self.assertEqual(pages[0]["markdown_chars"], 0)

    def test_crawl_stops_at_max_pages(self) -> None:
        smoke = load_smoke_module()

        pages = smoke.crawl(ROOT_ID, api=WideTreeAPI(), max_depth=1, max_pages=2)

        self.assertEqual([page["id"] for page in pages], [ROOT_ID, CHILD_ID])

    def test_crawl_marks_page_limit_truncation(self) -> None:
        smoke = load_smoke_module()

        pages = smoke.crawl(ROOT_ID, api=WideTreeAPI(), max_depth=1, max_pages=2)

        self.assertIs(pages[-1]["truncated_at_page_limit"], True)

    def test_direct_child_pages_rejects_non_uuid_block_ids(self) -> None:
        smoke = load_smoke_module()

        child_pages = smoke._direct_child_pages(
            [
                {
                    "id": "abc/../../../other",
                    "type": "child_page",
                    "child_page": {"title": "Bad"},
                },
                {
                    "id": CHILD_ID,
                    "type": "child_page",
                    "child_page": {"title": "Good"},
                },
            ]
        )

        self.assertEqual(child_pages, [{"id": CHILD_ID, "title": "Good"}])

    def test_list_block_children_paginates(self) -> None:
        api = PaginatedOfficialAPI()

        children = api.list_block_children(ROOT_ID)

        self.assertEqual(
            [child["id"] for child in children],
            ["paragraph-1", "paragraph-2"],
        )
        self.assertEqual(len(api.paths), 2)


if __name__ == "__main__":
    unittest.main()
