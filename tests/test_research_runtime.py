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
        "browser_created",
        "browser_closed",
        "job_finished",
        "research_finished",
    ]
    browser_event = events[2]
    assert browser_event["source_id"] == "baidu"
    assert browser_event["source_name"] == "Baidu web"
    assert browser_event["session_id"] == "session_123"
    assert (
        browser_event["inspect_url"]
        == "https://browser.lexmount.test/inspect/session_123"
    )
    assert events[3]["session_id"] == "session_123"


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
