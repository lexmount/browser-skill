from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from lex_browser_runtime import (
    ResearchJob,
    ResearchJobResult,
    route_research,
    run_research,
)
from lex_browser_runtime.cli import main as cli_main


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


def test_run_research_uses_concurrency_and_writes_artifacts(tmp_path: Path) -> None:
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
