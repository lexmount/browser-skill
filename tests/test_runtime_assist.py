from __future__ import annotations

import asyncio
from typing import Any

import pytest

from lex_browser_runtime import RuntimeAssist
from lex_browser_runtime.assist import (
    api,
    build_api_observation,
    compact_api_data,
    detect_douban_batch_completion_intent,
    fetch_api_via_http,
    has_answerable_runtime_state,
    is_allowed_douban_url,
)


def test_runtime_assist_compacts_and_summarizes_known_api() -> None:
    data = {
        "code": 0,
        "data": {
            "result": [
                {
                    "title": '【AI绘画】<em class="keyword">AI</em>教程',
                    "author": "秋葉aaaki",
                    "play": 7262219,
                    "video_review": 4584,
                    "duration": "03:59",
                    "pubdate": 1737426600,
                    "bvid": "BV1oXwmefEYy",
                    "arcurl": "https://www.bilibili.com/video/BV1oXwmefEYy/",
                }
            ]
        },
    }

    compact = compact_api_data(
        "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=AI",
        data,
    )
    observation = build_api_observation(
        "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=AI",
        data,
    )

    assert compact["bilibiliVideoSearch"] is True
    assert compact["items"][0]["title"] == "【AI绘画】AI教程"
    assert observation.runtime_compact_state is True
    assert "bilibili_video_search" in observation.summary


def test_runtime_assist_detects_answerable_state() -> None:
    assert (
        has_answerable_runtime_state(
            {"browser_api_call": {"status": 200, "runtime_compact_state": True}}
        )
        is True
    )
    assert (
        has_answerable_runtime_state(
            {"browser_api_call": {"status": 200, "blocked_page": True}}
        )
        is False
    )
    assert (
        has_answerable_runtime_state(
            {
                "browser_api_call": {
                    "status": 200,
                    "adapter_budget_reached": True,
                    "runtime_compact_state": True,
                }
            }
        )
        is False
    )
    assert (
        has_answerable_runtime_state(
            {"browser_api_call": {"status": 500, "runtime_compact_state": True}}
        )
        is False
    )
    assert (
        RuntimeAssist().has_answerable_runtime_state(
            {"page_program": {"ok": True, "results": [{"ok": True, "op": "click"}]}}
        )
        is False
    )


def test_douban_runtime_contract_detection_and_url_allowlist() -> None:
    assert (
        detect_douban_batch_completion_intent(
            'Search for 5 different books on Douban: "三体", "活着". Save all the collected data to JSON files.'
        )
        == "douban_book_batch"
    )
    assert (
        is_allowed_douban_url(
            "https://book.douban.com/subject/2567698/",
            required_host="book.douban.com",
        )
        is True
    )
    assert (
        is_allowed_douban_url(
            "http://book.douban.com/subject/2567698/",
            required_host="book.douban.com",
        )
        is False
    )
    assert (
        is_allowed_douban_url(
            "https://evil.example/subject/2567698/",
            required_host="book.douban.com",
        )
        is False
    )


def test_public_http_url_rejects_private_and_legacy_ip_forms() -> None:
    is_public = api.BROWSER_USE_SERVICE_COMPAT["is_public_http_url"]

    assert is_public("https://api.example.com/items") is True
    assert is_public("http://10.0.0.1/items") is False
    assert is_public("http://192.168.1.10/items") is False
    assert is_public("http://127.0.0.1/items") is False
    assert is_public("http://localhost/items") is False
    assert is_public("http://169.254.169.254/latest/meta-data") is False
    assert is_public("http://0177.0.0.1/items") is False
    assert is_public("http://127.1/items") is False
    assert is_public("http://2130706433/items") is False
    assert is_public("http://0x7f000001/items") is False


def test_fetch_api_via_http_rejects_private_redirect_before_following(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[str] = []

    class FakeRedirectResponse:
        url = "https://api.example.com/items"
        is_success = False
        status_code = 302
        headers = {"location": "http://169.254.169.254/latest/meta-data"}
        text = ""

        def json(self) -> dict[str, bool]:
            return {"ok": False}

    class FakeAsyncClient:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            assert kwargs["follow_redirects"] is False

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def request(
            self, method: str, url: str, **kwargs: Any
        ) -> FakeRedirectResponse:
            requests.append(url)
            return FakeRedirectResponse()

    monkeypatch.setattr(
        "lex_browser_runtime.assist.api.httpx.AsyncClient", FakeAsyncClient
    )

    with pytest.raises(ValueError, match="non-public URL"):
        asyncio.run(
            fetch_api_via_http("https://api.example.com/items", "GET", {}, None)
        )
    assert requests == ["https://api.example.com/items"]
