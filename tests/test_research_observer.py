from __future__ import annotations

import json
import threading
from types import SimpleNamespace
from urllib import request

from lex_browser_runtime.cli import main as cli_main
from lex_browser_runtime.observer import (
    ResearchObserver,
    create_observer_server,
    format_sse,
)


def test_format_sse_serializes_one_json_event() -> None:
    payload = format_sse({"type": "browser_created", "session_id": "session_123"})

    assert payload.startswith("data: ")
    assert payload.endswith("\n\n")
    assert json.loads(payload.removeprefix("data: ").strip()) == {
        "type": "browser_created",
        "session_id": "session_123",
    }


def test_research_observer_starts_run_and_records_browser_events() -> None:
    def fake_run_research(**kwargs: object) -> SimpleNamespace:
        assert kwargs["query"] == "最好吃的红烧肉"
        assert kwargs["sites"] == "baidu"
        assert kwargs["max_sites"] == 1
        assert kwargs["concurrency"] == 1
        assert kwargs["keep_sessions"] is True
        on_event = kwargs["on_event"]
        assert callable(on_event)
        on_event(
            {
                "type": "browser_created",
                "source_id": "baidu",
                "source_name": "Baidu web",
                "session_id": "session_123",
                "inspect_url": "https://browser.lexmount.test/inspect/session_123",
            }
        )
        return SimpleNamespace(
            ok=True,
            model_dump=lambda mode: {"ok": True, "summary_path": "/tmp/summary.json"},
        )

    observer = ResearchObserver(runner=fake_run_research)

    started = observer.start_research(
        query="最好吃的红烧肉",
        sites="baidu",
        max_sites=1,
        concurrency=1,
    )
    state = observer.wait_for_run(started["run_id"], timeout=1.0)

    assert state["status"] == "finished"
    assert state["summary"] == {"ok": True, "summary_path": "/tmp/summary.json"}
    assert state["active_sessions"] == [
        {
            "session_id": "session_123",
            "inspect_url": "https://browser.lexmount.test/inspect/session_123",
        }
    ]
    assert [event["type"] for event in state["events"]] == [
        "browser_created",
        "observer_run_finished",
    ]


def test_research_observer_builds_display_answer_from_summary() -> None:
    def fake_run_research(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            ok=True,
            model_dump=lambda mode: {
                "ok": True,
                "query": "best red-braised pork",
                "success_count": 1,
                "failure_count": 1,
                "results": [
                    {
                        "source_id": "baidu",
                        "source_name": "Baidu web",
                        "ok": True,
                        "title": "Baidu result title",
                        "text": "上海本帮冰糖红烧肉 带皮三层五花肉 冰糖炒糖色 小火慢炖 大火收汁",
                        "candidates": [
                            {
                                "text": "上海本帮冰糖红烧肉 带皮三层五花肉 冰糖炒糖色 小火慢炖 大火收汁",
                                "href": "https://example.test/restaurant",
                            }
                        ],
                    },
                    {
                        "source_id": "bing",
                        "source_name": "Bing web",
                        "ok": False,
                        "message": "blocked",
                    },
                ],
            },
        )

    observer = ResearchObserver(runner=fake_run_research)

    started = observer.start_research(query="best red-braised pork")
    state = observer.wait_for_run(started["run_id"], timeout=1.0)

    assert state["answer"] == {
        "ok": True,
        "query": "best red-braised pork",
        "source_summary": "1 succeeded, 1 failed",
        "summary_text": (
            "我用 Lexmount Browser 并发跑了 2 个来源。有效信息主要来自 Baidu web；"
            "另有 1 个来源失败或受限，参考价值较低。"
        ),
        "conclusion": (
            "结论：这类问题没有客观唯一的“最好吃”，但综合可用结果，"
            "最稳的方向是上海本帮/家常冰糖红烧肉：带皮三层五花肉、冰糖炒糖色、"
            "小火慢炖，最后大火收汁。"
        ),
        "recommendations": [
            "想吃经典甜口：选上海本帮红烧肉。",
            "想吃咸香浓郁：选东北/北方红烧肉。",
            "自己做时优先选带皮三层五花肉，先炒糖色，再小火慢炖，最后收汁。",
        ],
        "one_liner": (
            "一句话版：带皮三层五花肉 + 冰糖炒糖色 + 小火慢炖 + 大火收汁，"
            "是大众意义上最稳的红烧肉答案。"
        ),
        "source_note": "主要参考来源是 Baidu web。",
        "highlights": [
            {
                "source_name": "Baidu web",
                "title": "Baidu result title",
                "text": "上海本帮冰糖红烧肉 带皮三层五花肉 冰糖炒糖色 小火慢炖 大火收汁",
                "href": "https://example.test/restaurant",
            }
        ],
        "failures": [{"source_name": "Bing web", "message": "blocked"}],
    }


def test_research_observer_preserves_explicit_zero_concurrency() -> None:
    def fake_run_research(**kwargs: object) -> SimpleNamespace:
        assert kwargs["concurrency"] == 0
        return SimpleNamespace(ok=True, model_dump=lambda mode: {"ok": True})

    observer = ResearchObserver(runner=fake_run_research)

    started = observer.start_research(
        query="最好吃的红烧肉",
        sites="baidu",
        max_sites=1,
        concurrency=0,
    )
    state = observer.wait_for_run(started["run_id"], timeout=1.0)

    assert state["status"] == "finished"


def test_research_observer_close_run_removes_closed_sessions() -> None:
    closed: list[str] = []

    def fake_run_research(**kwargs: object) -> SimpleNamespace:
        on_event = kwargs["on_event"]
        assert callable(on_event)
        on_event(
            {
                "type": "browser_created",
                "source_id": "baidu",
                "source_name": "Baidu web",
                "session_id": "session_close",
                "inspect_url": "https://browser.lexmount.test/inspect/session_close",
            }
        )
        return SimpleNamespace(ok=True, model_dump=lambda mode: {"ok": True})

    observer = ResearchObserver(
        runner=fake_run_research,
        session_closer=closed.append,
    )
    started = observer.start_research(query="最好吃的红烧肉", sites="baidu")
    observer.wait_for_run(started["run_id"], timeout=1.0)

    close_result = observer.close_run(started["run_id"])

    assert close_result["closed"] == ["session_close"]
    assert closed == ["session_close"]
    assert observer.get_run(started["run_id"])["active_sessions"] == []


def test_observer_http_serves_page_and_accepts_research() -> None:
    def fake_run_research(**kwargs: object) -> SimpleNamespace:
        on_event = kwargs["on_event"]
        assert callable(on_event)
        on_event(
            {
                "type": "browser_created",
                "source_id": "baidu",
                "source_name": "Baidu web",
                "session_id": "session_http",
                "inspect_url": "https://browser.lexmount.test/inspect/session_http",
            }
        )
        return SimpleNamespace(ok=True, model_dump=lambda mode: {"ok": True})

    observer = ResearchObserver(runner=fake_run_research)
    server = create_observer_server(("127.0.0.1", 0), observer=observer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        html = request.urlopen(base_url, timeout=2).read().decode("utf-8")
        assert "Lexmount Research Observer" in html

        response = request.urlopen(
            request.Request(
                f"{base_url}/api/research",
                data=json.dumps(
                    {
                        "query": "最好吃的红烧肉",
                        "sites": "baidu",
                        "max_sites": 1,
                        "concurrency": 1,
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=2,
        )
        started = json.loads(response.read())
        state = observer.wait_for_run(started["run_id"], timeout=1.0)

        response = request.urlopen(
            f"{base_url}/api/runs/{started['run_id']}",
            timeout=2,
        )
        payload = json.loads(response.read())
        assert payload["status"] == state["status"] == "finished"
        assert payload["active_sessions"][0]["session_id"] == "session_http"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_observer_http_accepts_external_run_events() -> None:
    observer = ResearchObserver()
    server = create_observer_server(("127.0.0.1", 0), observer=observer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        response = request.urlopen(
            request.Request(
                f"{base_url}/api/runs",
                data=json.dumps(
                    {"run_id": "codex-run-1", "query": "最好吃的红烧肉"}
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=2,
        )
        assert json.loads(response.read())["run_id"] == "codex-run-1"

        event_response = request.urlopen(
            request.Request(
                f"{base_url}/api/runs/codex-run-1/events",
                data=json.dumps(
                    {
                        "type": "browser_created",
                        "source_id": "baidu",
                        "source_name": "Baidu web",
                        "session_id": "session_external",
                        "inspect_url": "https://browser.lexmount.test/inspect/session_external",
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=2,
        )
        assert json.loads(event_response.read())["ok"] is True

        latest = json.loads(
            request.urlopen(f"{base_url}/api/runs/latest", timeout=2).read()
        )
        assert latest["run_id"] == "codex-run-1"
        assert latest["active_sessions"][0]["session_id"] == "session_external"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_observer_http_finishes_external_run_with_summary_answer() -> None:
    observer = ResearchObserver()
    server = create_observer_server(("127.0.0.1", 0), observer=observer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        request.urlopen(
            request.Request(
                f"{base_url}/api/runs",
                data=json.dumps(
                    {"run_id": "codex-run-finish", "query": "最好吃的红烧肉"}
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=2,
        ).read()

        finish_response = request.urlopen(
            request.Request(
                f"{base_url}/api/runs/codex-run-finish/events",
                data=json.dumps(
                    {
                        "type": "observer_run_finished",
                        "status": "finished",
                        "summary": {
                            "ok": True,
                            "query": "最好吃的红烧肉",
                            "success_count": 1,
                            "failure_count": 0,
                            "results": [
                                {
                                    "source_id": "baidu",
                                    "source_name": "Baidu web",
                                    "ok": True,
                                    "title": "Baidu result title",
                                    "text": "上海本帮冰糖红烧肉 带皮三层五花肉",
                                }
                            ],
                        },
                    }
                ).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=2,
        )
        assert json.loads(finish_response.read())["status"] == "finished"

        state = json.loads(
            request.urlopen(f"{base_url}/api/runs/codex-run-finish", timeout=2).read()
        )
        assert state["status"] == "finished"
        assert state["summary"]["success_count"] == 1
        assert state["answer"]["query"] == "最好吃的红烧肉"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_observer_keeps_external_run_open_after_research_finished() -> None:
    observer = ResearchObserver()
    observer.create_observed_run(run_id="codex-run-stream", query="query")

    result = observer.record_external_event(
        "codex-run-stream",
        {
            "type": "research_finished",
            "ok": True,
            "success_count": 1,
            "failure_count": 0,
        },
    )

    assert result["status"] == "running"
    assert observer.get_run("codex-run-stream")["status"] == "running"


def test_observer_page_prioritizes_large_five_column_browser_grid() -> None:
    server = create_observer_server(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        html = request.urlopen(base_url, timeout=2).read().decode("utf-8")

        assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in html
        assert "grid-template-columns: minmax(220px, 280px) 1fr;" in html
        assert "grid-template-columns: 48px 1fr;" in html
        assert 'id="toggleSidebar"' in html
        assert "sidebar-collapsed" in html
        assert "height: clamp(620px, 70vh, 860px);" in html
        assert 'id="eventList"' in html
        assert 'id="answerPanel"' in html
        assert "renderAnswer" in html
        assert 'id="researchForm"' in html
        assert 'id="query"' in html
        assert 'id="query" name="query" value="" autocomplete="off"' in html
        assert 'value="最好吃的红烧肉"' not in html
        assert "new EventSource(`/api/runs/${currentRunId}/events`)" in html
        assert '"/api/research"' in html
        assert '"/api/runs/latest"' in html
        assert 'preset: "food"' in html
        assert "max_sites: 5" in html
        assert "concurrency: 5" in html
        assert "answer.summary_text" in html
        assert "answer.conclusion" in html
        assert "answer.recommendations" in html
        assert "answer.one_liner" in html
        assert "answer.source_note" in html
        assert "answer-list" not in html
        assert 'id="sites"' not in html
        assert "form.sites.value" not in html
        assert 'id="maxSites"' not in html
        assert "form.maxSites.value" not in html
        assert "JSON.stringify(event)" not in html
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_cli_observer_serve_invokes_local_server(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_serve_observer(*, host: str, port: int) -> None:
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setattr("lex_browser_runtime.cli.serve_observer", fake_serve_observer)

    cli_main(["observer", "serve", "--host", "127.0.0.1", "--port", "8765"])

    assert captured == {"host": "127.0.0.1", "port": 8765}
