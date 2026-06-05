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


def test_runtime_assist_compacts_docin_search_results() -> None:
    html = """
    <html><head><title>按 市场营销方案 搜索结果列表 - Docin.com豆丁网</title></head>
    <body>
    <div class="doc-list-style2 doc-mark">
      <dl class="clear">
        <dt class="imgs"><a href="/p-3463806101.html"><span class="pageno">10</span></a></dt>
        <dd class="fc-baidu title">
          <a title="营销方案市场营销方案（市场营销资料）.doc" href="/p-3463806101.html">
            <em class="doc-list-title-inline">营销方案市场营销方案</em>.doc
          </a>
        </dd>
        <dd class="summary"><a href="/p-3463806101.html">本文是市场营销表格模板参考范文。</a></dd>
        <dd><ul><li>上传于2025-05-12</li></ul></dd>
      </dl>
    </div>
    </body></html>
    """

    url = "https://www.docin.com/search.do?searchcat=1001&dt=3&od=2&numpage=2&yearType=1&nkey=%E5%B8%82%E5%9C%BA%E8%90%A5%E9%94%80%E6%96%B9%E6%A1%88"
    compact = compact_api_data(url, html)
    observation = build_api_observation(url, html)

    assert compact["docinSearchResult"] is True
    assert compact["query"] == "市场营销方案"
    assert compact["filters"] == {
        "format": "ppt",
        "sort": "most_read",
        "pageRangeHint": "9-100",
        "yearBucket": "current_calendar_year",
    }
    assert compact["items"][0]["id"] == "3463806101"
    assert compact["items"][0]["pageCount"] == 10
    assert compact["items"][0]["format"] == ".doc"
    assert compact["items"][0]["url"] == "https://www.docin.com/p-3463806101.html"
    assert observation.runtime_compact_state is True
    assert "docin_search" in observation.summary


def test_runtime_assist_compacts_gamespot_review_search() -> None:
    data = [
        {
            "id": 1158242,
            "title": "The Legend Of Zelda: Tears Of The Kingdom Review",
            "url": "https://www.gamespot.com/reviews/the-legend-of-zelda-tears-of-the-kingdom-review/1900-6418063/",
            "type": "post",
            "subtype": "reviews",
            "_links": {
                "self": [
                    {
                        "href": "https://www.gamespot.com/wp-json/wp/v2/reviews/1158242",
                        "targetHints": {"allow": ["GET"]},
                    }
                ]
            },
        }
    ]

    url = "https://www.gamespot.com/wp-json/wp/v2/search?search=The%20Legend%20of%20Zelda%20Tears%20of%20the%20Kingdom%20review&subtype=reviews&per_page=20"
    compact = compact_api_data(url, data)
    observation = build_api_observation(url, data)

    assert compact["gamespotReviewSearch"] is True
    assert compact["query"] == "The Legend of Zelda Tears of the Kingdom review"
    assert compact["items"][0]["id"] == 1158242
    assert (
        compact["items"][0]["apiUrl"]
        == "https://www.gamespot.com/wp-json/wp/v2/reviews/1158242"
    )
    assert observation.runtime_compact_state is True
    assert "gamespot_review_search" in observation.summary


def test_runtime_assist_compacts_gamespot_review_detail() -> None:
    data = {
        "id": 1158242,
        "date": "2023-05-11T12:00:00",
        "link": "https://www.gamespot.com/reviews/the-legend-of-zelda-tears-of-the-kingdom-review/1900-6418063/",
        "title": {"rendered": "The Legend Of Zelda: Tears Of The Kingdom Review"},
        "_embedded": {"author": [{"name": "Steve Watts"}]},
        "meta": {"review_score": "10"},
        "content": {
            "rendered": """
            <h2>The Good</h2>
            <ul><li>Huge, systems-rich world</li><li>Creative building tools</li></ul>
            <h2>The Bad</h2>
            <ul><li>Some performance dips</li></ul>
            <h2>Verdict</h2>
            <p>A remarkable open-world adventure.</p>
            """
        },
    }

    url = "https://www.gamespot.com/wp-json/wp/v2/reviews/1158242?_embed=1"
    compact = compact_api_data(url, data)
    observation = build_api_observation(url, data)

    assert compact["gamespotReviewDetail"] is True
    assert compact["id"] == 1158242
    assert compact["title"] == "The Legend Of Zelda: Tears Of The Kingdom Review"
    assert compact["score"] == "10"
    assert compact["reviewer"] == "Steve Watts"
    assert "Huge, systems-rich world" in compact["pros"][0]
    assert "performance dips" in compact["cons"][0]
    assert observation.runtime_compact_state is True
    assert "gamespot_review_detail" in observation.summary


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
    assert (
        RuntimeAssist().has_answerable_runtime_state(
            {
                "page_program": {
                    "ok": True,
                    "results": [
                        {"ok": True, "op": "click", "target_id": "text:Search"}
                    ],
                    "state": {"text:Search": {"value": "", "text": "Search"}},
                }
            }
        )
        is False
    )
    assert (
        RuntimeAssist().has_answerable_runtime_state(
            {
                "page_program": {
                    "ok": True,
                    "results": [
                        {"ok": True, "op": "click", "target_id": "text:In-store"}
                    ],
                    "state": {"text:In-store": {"value": "", "text": "In-store"}},
                },
                "runtime_compact_state": True,
            }
        )
        is True
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
