from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from lex_browser_runtime import (
    ResearchJob,
    ResearchJobResult,
    route_research,
    run_research,
)
from lex_browser_runtime.cli import main as cli_main
from lex_browser_runtime.config import (
    DEFAULT_RESEARCH_CONCURRENCY,
    RESEARCH_CONCURRENCY_ENV,
)


def test_route_research_food_preset_builds_ten_source_jobs() -> None:
    route = route_research(query="最好吃的红烧肉", preset="food")

    assert route.ok is True
    assert route.query == "最好吃的红烧肉"
    assert len(route.jobs) == 10
    assert [job.source_id for job in route.jobs[:3]] == [
        "baidu",
        "bing",
        "xiaohongshu",
    ]
    assert "%E6%9C%80%E5%A5%BD%E5%90%83%E7%9A%84%E7%BA%A2%E7%83%A7%E8%82%89" in (
        route.jobs[0].url
    )


def test_route_research_filters_sites_in_requested_order() -> None:
    route = route_research(
        query="best ramen",
        preset="food",
        sites="bilibili,baidu",
        max_sites=10,
    )

    assert [job.source_id for job in route.jobs] == ["bilibili", "baidu"]
    assert route.jobs[0].rank == 1
    assert "best%20ramen" in route.jobs[0].url


def test_cli_research_route_outputs_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli_main(
            [
                "research",
                "route",
                "--query",
                "最好吃的红烧肉",
                "--sites",
                "baidu,bing",
            ]
        )

    assert exc_info.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "research.route"
    assert payload["query"] == "最好吃的红烧肉"
    assert [job["source_id"] for job in payload["jobs"]] == ["baidu", "bing"]


def test_cli_research_run_defaults_to_parallel_concurrency(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(RESEARCH_CONCURRENCY_ENV, raising=False)
    captured: dict[str, object] = {}

    class FakeSummary:
        ok = True

        def model_dump(self, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "command": "research.run",
                "concurrency": captured["concurrency"],
                "ok": True,
            }

    def fake_run_research(**kwargs: object) -> FakeSummary:
        captured.update(kwargs)
        return FakeSummary()

    monkeypatch.setattr(
        "lex_browser_runtime.cli.run_research",
        fake_run_research,
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main(
            [
                "research",
                "run",
                "--query",
                "最好吃的红烧肉",
                "--sites",
                "baidu,bing",
            ]
        )

    assert exc_info.value.code == 0
    assert captured["concurrency"] == DEFAULT_RESEARCH_CONCURRENCY
    payload = json.loads(capsys.readouterr().out)
    assert payload["concurrency"] == DEFAULT_RESEARCH_CONCURRENCY


def test_cli_research_run_uses_configured_default_concurrency(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RESEARCH_CONCURRENCY_ENV, "3")
    captured: dict[str, object] = {}

    class FakeSummary:
        ok = True

        def model_dump(self, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "command": "research.run",
                "concurrency": captured["concurrency"],
                "ok": True,
            }

    def fake_run_research(**kwargs: object) -> FakeSummary:
        captured.update(kwargs)
        return FakeSummary()

    monkeypatch.setattr(
        "lex_browser_runtime.cli.run_research",
        fake_run_research,
    )

    with pytest.raises(SystemExit) as exc_info:
        cli_main(
            [
                "research",
                "run",
                "--query",
                "最好吃的红烧肉",
                "--sites",
                "baidu,bing",
            ]
        )

    assert exc_info.value.code == 0
    assert captured["concurrency"] == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["concurrency"] == 3


def test_cli_research_run_pushes_events_to_observer(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    publisher_events: list[dict[str, object]] = []
    publisher_finishes: list[dict[str, object]] = []

    class FakePublisher:
        def __init__(self, observer_url: str, *, run_id: str, query: str) -> None:
            captured["observer_url"] = observer_url
            captured["run_id"] = run_id
            captured["query"] = query

        def __enter__(self) -> "FakePublisher":
            captured["entered"] = True
            return self

        def __exit__(self, *args: object) -> None:
            captured["exited"] = True

        def emit(self, event: dict[str, object]) -> None:
            publisher_events.append(event)

        def finish(self, summary: dict[str, object]) -> None:
            publisher_finishes.append(summary)

    class FakeSummary:
        ok = True

        def model_dump(self, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {"ok": True, "run_id": captured["run_id"]}

    def fake_run_research(**kwargs: object) -> FakeSummary:
        captured.update(kwargs)
        on_event = kwargs["on_event"]
        assert callable(on_event)
        on_event({"type": "browser_created", "session_id": "session_observed"})
        return FakeSummary()

    monkeypatch.setattr(
        "lex_browser_runtime.cli.ObserverEventPublisher",
        FakePublisher,
    )
    monkeypatch.setattr("lex_browser_runtime.cli.run_research", fake_run_research)

    with pytest.raises(SystemExit) as exc_info:
        cli_main(
            [
                "research",
                "run",
                "--query",
                "最好吃的红烧肉",
                "--observer-url",
                "http://127.0.0.1:8765",
                "--run-id",
                "codex-run-1",
            ]
        )

    assert exc_info.value.code == 0
    assert captured["observer_url"] == "http://127.0.0.1:8765"
    assert captured["run_id"] == "codex-run-1"
    assert captured["query"] == "最好吃的红烧肉"
    assert publisher_events == [
        {"type": "browser_created", "session_id": "session_observed"}
    ]
    assert publisher_finishes == [{"ok": True, "run_id": "codex-run-1"}]
    assert captured["entered"] is True
    assert captured["exited"] is True
    assert json.loads(capsys.readouterr().out)["run_id"] == "codex-run-1"


def test_cli_research_run_uses_observer_url_env(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    publisher_finishes: list[dict[str, object]] = []

    class FakePublisher:
        def __init__(self, observer_url: str, *, run_id: str, query: str) -> None:
            captured["observer_url"] = observer_url
            captured["run_id"] = run_id
            captured["query"] = query

        def __enter__(self) -> "FakePublisher":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def emit(self, event: dict[str, object]) -> None:
            captured["event"] = event

        def finish(self, summary: dict[str, object]) -> None:
            publisher_finishes.append(summary)

    class FakeSummary:
        ok = True

        def model_dump(self, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {"ok": True, "run_id": captured["run_id"]}

    def fake_run_research(**kwargs: object) -> FakeSummary:
        captured.update(kwargs)
        on_event = kwargs["on_event"]
        assert callable(on_event)
        on_event({"type": "browser_created", "session_id": "session_env"})
        return FakeSummary()

    monkeypatch.setenv("LEX_BROWSER_OBSERVER_URL", "http://127.0.0.1:8765")
    monkeypatch.setattr(
        "lex_browser_runtime.cli.ObserverEventPublisher",
        FakePublisher,
    )
    monkeypatch.setattr("lex_browser_runtime.cli.run_research", fake_run_research)

    with pytest.raises(SystemExit) as exc_info:
        cli_main(
            [
                "research",
                "run",
                "--query",
                "最好吃的红烧肉",
                "--run-id",
                "codex-env-run",
            ]
        )

    assert exc_info.value.code == 0
    assert captured["observer_url"] == "http://127.0.0.1:8765"
    assert captured["run_id"] == "codex-env-run"
    assert captured["event"] == {"type": "browser_created", "session_id": "session_env"}
    assert publisher_finishes == [{"ok": True, "run_id": "codex-env-run"}]
    assert json.loads(capsys.readouterr().out)["run_id"] == "codex-env-run"


def test_cli_research_run_forwards_auth_contexts_file(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    auth_contexts_file = tmp_path / "auth-contexts.json"
    auth_contexts_file.write_text(
        json.dumps(
            {
                "version": 1,
                "contexts": {
                    "xiaohongshu": {
                        "context_id": "ctx_xhs",
                        "context_mode": "read_only",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    class FakeSummary:
        ok = True

        def model_dump(self, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "command": "research.run",
                "auth_contexts_file": str(captured["auth_contexts_file"]),
                "ok": True,
            }

    def fake_run_research(**kwargs: object) -> FakeSummary:
        captured.update(kwargs)
        return FakeSummary()

    monkeypatch.setattr("lex_browser_runtime.cli.run_research", fake_run_research)

    with pytest.raises(SystemExit) as exc_info:
        cli_main(
            [
                "research",
                "run",
                "--query",
                "最好吃的红烧肉",
                "--sites",
                "xiaohongshu",
                "--auth-contexts-file",
                str(auth_contexts_file),
            ]
        )

    assert exc_info.value.code == 0
    assert captured["auth_contexts_file"] == str(auth_contexts_file)
    assert json.loads(capsys.readouterr().out)["auth_contexts_file"] == str(
        auth_contexts_file
    )


def test_run_research_uses_concurrency_and_writes_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RESEARCH_CONCURRENCY_ENV, "3")
    lock = threading.Lock()
    active = 0
    max_active = 0

    def fake_job_runner(job: ResearchJob) -> ResearchJobResult:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        try:
            time.sleep(0.05)
            return ResearchJobResult(
                source_id=job.source_id,
                source_name=job.source_name,
                url=job.url,
                ok=True,
                duration_ms=50.0,
                final_url=job.url,
                title=f"{job.source_name} result",
                text=f"{job.query} evidence from {job.source_name}",
            )
        finally:
            with lock:
                active -= 1

    summary = run_research(
        query="最好吃的红烧肉",
        sites="baidu,bing,xiaohongshu,bilibili",
        concurrency=2,
        output_dir=tmp_path,
        run_id="demo",
        job_runner=fake_job_runner,
    )

    assert summary.ok is True
    assert summary.success_count == 4
    assert summary.failure_count == 0
    assert summary.concurrency == 2
    assert max_active == 2
    output_dir = tmp_path / "demo"
    assert Path(summary.output_dir) == output_dir
    assert Path(summary.summary_path) == output_dir / "summary.json"
    assert (output_dir / "routes.json").exists()
    assert (output_dir / "sources.jsonl").exists()
    assert (output_dir / "events.jsonl").exists()
    assert json.loads((output_dir / "summary.json").read_text())["success_count"] == 4


def test_run_research_emits_live_browser_created_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []

    class FakeAdmin:
        def create_session(self, *, browser_mode: str) -> SimpleNamespace:
            assert browser_mode == "normal"
            return SimpleNamespace(
                session=SimpleNamespace(
                    session_id="session_123",
                    inspect_url="https://browser.lexmount.test/inspect/session_123",
                    inspect_url_dbg=None,
                    connect_url="wss://cdp.lexmount.test/session_123",
                )
            )

        def close_session(self, session_id: str) -> None:
            assert session_id == "session_123"

    def fake_extract_page_data(**kwargs: object) -> dict[str, object]:
        assert kwargs["connect_url"] == "wss://cdp.lexmount.test/session_123"
        assert kwargs["url"].startswith("https://www.baidu.com/s")
        return {
            "final_url": kwargs["url"],
            "title": "Baidu result",
            "text": "visible evidence",
            "headings": [],
            "links": [],
            "candidates": [],
            "status": 200,
        }

    monkeypatch.setattr(
        "lex_browser_runtime.research._extract_page_data",
        fake_extract_page_data,
    )

    summary = run_research(
        query="最好吃的红烧肉",
        sites="baidu",
        max_sites=1,
        concurrency=1,
        output_dir=tmp_path,
        run_id="live",
        admin_factory=FakeAdmin,
        on_event=events.append,
    )

    assert summary.ok is True
    event_types = [event["type"] for event in events]
    assert event_types == [
        "research_started",
        "job_started",
        "session_create_started",
        "browser_created",
        "browser_closed",
        "job_finished",
        "research_finished",
    ]
    browser_event = events[3]
    assert browser_event["source_id"] == "baidu"
    assert browser_event["source_name"] == "Baidu web"
    assert browser_event["session_id"] == "session_123"
    assert (
        browser_event["inspect_url"]
        == "https://browser.lexmount.test/inspect/session_123"
    )
    assert events[4]["session_id"] == "session_123"


def test_run_research_uses_saved_auth_context_for_matching_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_contexts_file = tmp_path / "auth-contexts.json"
    auth_contexts_file.write_text(
        json.dumps(
            {
                "version": 1,
                "contexts": {
                    "xiaohongshu": {
                        "context_id": "ctx_xhs",
                        "context_mode": "read_only",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    create_calls: list[dict[str, object]] = []
    close_calls: list[str] = []

    class FakeAdmin:
        def create_session(
            self,
            *,
            browser_mode: str,
            context_id: str | None = None,
            context_mode: str = "read_write",
        ) -> SimpleNamespace:
            create_calls.append(
                {
                    "browser_mode": browser_mode,
                    "context_id": context_id,
                    "context_mode": context_mode,
                }
            )
            return SimpleNamespace(
                session=SimpleNamespace(
                    session_id="session_xhs",
                    inspect_url="https://browser.lexmount.test/inspect/session_xhs",
                    inspect_url_dbg=None,
                    connect_url="wss://cdp.lexmount.test/session_xhs",
                )
            )

        def close_session(self, session_id: str) -> None:
            close_calls.append(session_id)

    def fake_extract_page_data(**kwargs: object) -> dict[str, object]:
        assert kwargs["connect_url"] == "wss://cdp.lexmount.test/session_xhs"
        return {
            "final_url": kwargs["url"],
            "title": "Xiaohongshu result",
            "text": "visible logged-in evidence",
            "headings": [],
            "links": [],
            "candidates": [],
            "status": 200,
        }

    monkeypatch.setattr(
        "lex_browser_runtime.research._extract_page_data",
        fake_extract_page_data,
    )

    summary = run_research(
        query="最好吃的红烧肉",
        sites="xiaohongshu",
        max_sites=1,
        concurrency=1,
        output_dir=tmp_path,
        run_id="auth-context",
        admin_factory=FakeAdmin,
        auth_contexts_file=auth_contexts_file,
    )

    assert summary.ok is True
    assert create_calls == [
        {
            "browser_mode": "normal",
            "context_id": "ctx_xhs",
            "context_mode": "read_only",
        },
    ]
    assert close_calls == ["session_xhs"]
    assert summary.results[0].auth_context_id == "ctx_xhs"
    assert summary.results[0].auth_context_mode == "read_only"


def test_run_research_preallocates_auth_context_sessions_before_public_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_contexts_file = tmp_path / "auth-contexts.json"
    auth_contexts_file.write_text(
        json.dumps(
            {
                "version": 1,
                "contexts": {
                    "xiaohongshu": {
                        "context_id": "ctx_xhs",
                        "context_mode": "read_write",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    create_calls: list[str] = []
    events: list[dict[str, object]] = []

    class FakeAdmin:
        def create_session(
            self,
            *,
            browser_mode: str,
            context_id: str | None = None,
            context_mode: str = "read_write",
        ) -> SimpleNamespace:
            source = "xiaohongshu" if context_id == "ctx_xhs" else "public"
            create_calls.append(source)
            return SimpleNamespace(
                session=SimpleNamespace(
                    session_id=f"session_{source}_{len(create_calls)}",
                    inspect_url=f"https://browser.lexmount.test/{source}",
                    inspect_url_dbg=None,
                    connect_url=f"wss://cdp.lexmount.test/{source}",
                )
            )

        def close_session(self, session_id: str) -> None:
            return None

    def fake_extract_page_data(**kwargs: object) -> dict[str, object]:
        return {
            "final_url": kwargs["url"],
            "title": "result",
            "text": "visible evidence",
            "headings": [],
            "links": [],
            "candidates": [],
            "status": 200,
        }

    monkeypatch.setattr(
        "lex_browser_runtime.research._extract_page_data",
        fake_extract_page_data,
    )

    summary = run_research(
        query="最好吃的红烧肉",
        sites="baidu,xiaohongshu,bing",
        concurrency=3,
        output_dir=tmp_path,
        run_id="auth-first",
        admin_factory=FakeAdmin,
        auth_contexts_file=auth_contexts_file,
        on_event=events.append,
    )

    assert summary.ok is True
    assert create_calls[0] == "xiaohongshu"
    assert create_calls.count("xiaohongshu") == 1
    assert create_calls.count("public") == 2
    assert events[0]["type"] == "research_started"
    assert events[0]["jobs"] == [
        {
            "rank": 1,
            "source_id": "baidu",
            "source_name": "Baidu web",
            "url": summary.jobs[0].url,
        },
        {
            "rank": 2,
            "source_id": "xiaohongshu",
            "source_name": "Xiaohongshu",
            "url": summary.jobs[1].url,
        },
        {
            "rank": 3,
            "source_id": "bing",
            "source_name": "Bing web",
            "url": summary.jobs[2].url,
        },
    ]
    prepared_events = [
        event for event in events if event["type"] == "browser_prepared"
    ]
    assert len(prepared_events) == 1
    assert prepared_events[0]["source_id"] == "xiaohongshu"
    created_events = [
        event
        for event in events
        if event["type"] == "browser_created"
        and event.get("source_id") == "xiaohongshu"
    ]
    assert len(created_events) == 1
    assert created_events[0]["session_id"] == prepared_events[0]["session_id"]
    assert events.index(prepared_events[0]) < events.index(created_events[0])


def test_run_research_records_auth_context_session_allocation_failure(
    tmp_path: Path,
) -> None:
    auth_contexts_file = tmp_path / "auth-contexts.json"
    auth_contexts_file.write_text(
        json.dumps(
            {
                "version": 1,
                "contexts": {
                    "zhihu": {
                        "context_id": "ctx_zhihu",
                        "context_mode": "read_write",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    events: list[dict[str, object]] = []
    create_calls: list[dict[str, object]] = []

    class FakeAdmin:
        def create_session(
            self,
            *,
            browser_mode: str,
            context_id: str | None = None,
            context_mode: str = "read_write",
        ) -> SimpleNamespace:
            create_calls.append(
                {
                    "browser_mode": browser_mode,
                    "context_id": context_id,
                    "context_mode": context_mode,
                }
            )
            raise RuntimeError("context session did not become ready")

        def close_session(self, session_id: str) -> None:
            raise AssertionError(f"unexpected close for {session_id}")

    summary = run_research(
        query="最好吃的红烧肉",
        sites="zhihu",
        max_sites=1,
        concurrency=1,
        output_dir=tmp_path,
        run_id="auth-session-allocation-failure",
        admin_factory=FakeAdmin,
        auth_contexts_file=auth_contexts_file,
        on_event=events.append,
    )

    assert summary.ok is False
    assert summary.success_count == 0
    assert summary.failure_count == 1
    assert create_calls == [
        {
            "browser_mode": "normal",
            "context_id": "ctx_zhihu",
            "context_mode": "read_write",
        }
    ]
    assert summary.results[0].source_id == "zhihu"
    assert summary.results[0].auth_context_id == "ctx_zhihu"
    assert summary.results[0].error == "RuntimeError"
    assert summary.results[0].message == (
        "Failed to create Lexmount session before research: "
        "context session did not become ready"
    )
    event_types = [event["type"] for event in events]
    assert event_types == [
        "research_started",
        "session_create_started",
        "session_create_failed",
        "job_finished",
        "research_finished",
    ]
    assert (tmp_path / "auth-session-allocation-failure" / "summary.json").exists()
    source_lines = (
        tmp_path / "auth-session-allocation-failure" / "sources.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert len(source_lines) == 1
    assert json.loads(source_lines[0])["source_id"] == "zhihu"


def test_run_research_times_out_slow_auth_context_session_allocation(
    tmp_path: Path,
) -> None:
    auth_contexts_file = tmp_path / "auth-contexts.json"
    auth_contexts_file.write_text(
        json.dumps(
            {
                "version": 1,
                "contexts": {
                    "xiaohongshu": {
                        "context_id": "ctx_xhs",
                        "context_mode": "read_write",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    close_calls: list[str] = []

    class FakeAdmin:
        def create_session(
            self,
            *,
            browser_mode: str,
            context_id: str | None = None,
            context_mode: str = "read_write",
        ) -> SimpleNamespace:
            time.sleep(0.3)
            return SimpleNamespace(session=SimpleNamespace(session_id="late_session"))

        def close_session(self, session_id: str) -> None:
            close_calls.append(session_id)

    summary = run_research(
        query="最好吃的红烧肉",
        sites="xiaohongshu",
        max_sites=1,
        concurrency=1,
        output_dir=tmp_path,
        run_id="auth-session-allocation-timeout",
        admin_factory=FakeAdmin,
        auth_contexts_file=auth_contexts_file,
        session_create_timeout_sec=0.1,
    )

    assert summary.ok is False
    assert summary.results[0].source_id == "xiaohongshu"
    assert summary.results[0].error == "BrowserRuntimeError"
    assert summary.results[0].message == (
        "Failed to create Lexmount session before research: "
        "Timed out creating Lexmount session after 0.1s"
    )
    deadline = time.time() + 1.0
    while not close_calls and time.time() < deadline:
        time.sleep(0.01)
    assert close_calls == ["late_session"]
    assert (tmp_path / "auth-session-allocation-timeout" / "summary.json").exists()


def test_run_research_emits_failure_message_in_live_events(tmp_path: Path) -> None:
    events: list[dict[str, object]] = []

    def fake_job_runner(job: ResearchJob) -> ResearchJobResult:
        return ResearchJobResult(
            source_id=job.source_id,
            source_name=job.source_name,
            url=job.url,
            ok=False,
            duration_ms=10.0,
            error="BrowserParallelLimitError",
            message="浏览器并行额度已达上限，当前无法创建新的 browser，请先关闭部分 session 后重试。",
        )

    run_research(
        query="最好吃的红烧肉",
        sites="baidu",
        max_sites=1,
        concurrency=1,
        output_dir=tmp_path,
        run_id="failure-message",
        job_runner=fake_job_runner,
        on_event=events.append,
    )

    finished = next(event for event in events if event["type"] == "job_finished")
    assert finished["error"] == "BrowserParallelLimitError"
    assert finished["message"] == (
        "浏览器并行额度已达上限，当前无法创建新的 browser，请先关闭部分 session 后重试。"
    )
