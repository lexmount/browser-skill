"""Multi-source Lexmount browser research runner."""

from __future__ import annotations

import concurrent.futures
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field

from lex_browser_runtime.browser.lexmount import LexmountBrowserAdmin
from lex_browser_runtime.browser.models import BrowserConfigError, BrowserRuntimeError
from lex_browser_runtime.config import get_default_research_concurrency

ResearchPreset = Literal["food", "web"]
ResearchEventSink = Callable[[dict[str, Any]], None]


class ResearchSource(BaseModel):
    """One routeable public web source for runtime research."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    name: str
    url_template: str
    source_type: str = "search"
    notes: str | None = None


class ResearchJob(BaseModel):
    """One source-specific browser job derived from a natural-language query."""

    rank: int
    query: str
    preset: str
    source_id: str
    source_name: str
    source_type: str
    url: str
    extraction_goal: str


class ResearchRoute(BaseModel):
    """A deterministic research route that an outer agent can inspect."""

    ok: bool = True
    command: str = "research.route"
    query: str
    preset: str
    jobs: list[ResearchJob]


class ResearchLink(BaseModel):
    """A compact link extracted from one source page."""

    text: str
    href: str


class ResearchCandidate(BaseModel):
    """A compact visible result/card extracted from one source page."""

    text: str
    href: str | None = None


class ResearchJobResult(BaseModel):
    """Result from one browser-backed source job."""

    source_id: str
    source_name: str
    url: str
    ok: bool
    duration_ms: float
    session_id: str | None = None
    inspect_url: str | None = None
    final_url: str | None = None
    title: str | None = None
    status: int | None = None
    text: str | None = None
    headings: list[str] = Field(default_factory=list)
    links: list[ResearchLink] = Field(default_factory=list)
    candidates: list[ResearchCandidate] = Field(default_factory=list)
    error: str | None = None
    message: str | None = None


class ResearchRunSummary(BaseModel):
    """Summary and artifact locations for one multi-source research run."""

    ok: bool
    command: str = "research.run"
    query: str
    preset: str
    run_id: str
    output_dir: str
    events_path: str
    sources_path: str
    routes_path: str
    summary_path: str
    success_count: int
    failure_count: int
    concurrency: int
    jobs: list[ResearchJob]
    results: list[ResearchJobResult]


FOOD_SOURCES: tuple[ResearchSource, ...] = (
    ResearchSource(
        source_id="baidu",
        name="Baidu web",
        url_template="https://www.baidu.com/s?wd={query}",
        notes="Broad Chinese web results.",
    ),
    ResearchSource(
        source_id="bing",
        name="Bing web",
        url_template="https://www.bing.com/search?q={query}",
        notes="General search fallback.",
    ),
    ResearchSource(
        source_id="xiaohongshu",
        name="Xiaohongshu",
        url_template="https://www.xiaohongshu.com/search_result?keyword={query}",
        notes="User-generated food recommendations.",
    ),
    ResearchSource(
        source_id="bilibili",
        name="Bilibili",
        url_template="https://search.bilibili.com/all?keyword={query}",
        notes="Video results and food creator recommendations.",
    ),
    ResearchSource(
        source_id="zhihu",
        name="Zhihu",
        url_template="https://www.zhihu.com/search?type=content&q={query}",
        notes="Long-form discussion and local recommendation threads.",
    ),
    ResearchSource(
        source_id="douyin",
        name="Douyin",
        url_template="https://www.douyin.com/search/{query}",
        notes="Short-video food discovery surface.",
    ),
    ResearchSource(
        source_id="amap",
        name="Amap",
        url_template="https://www.amap.com/search?query={query}",
        notes="Map-local restaurant candidates.",
    ),
    ResearchSource(
        source_id="ctrip",
        name="Ctrip travel",
        url_template="https://you.ctrip.com/searchsite/?query={query}",
        notes="Travel and local guide search.",
    ),
    ResearchSource(
        source_id="mafengwo",
        name="Mafengwo",
        url_template="https://www.mafengwo.cn/search/q.php?q={query}",
        notes="Travel guide and local food notes.",
    ),
    ResearchSource(
        source_id="weibo",
        name="Weibo search",
        url_template="https://s.weibo.com/weibo?q={query}",
        notes="Recent social discussion.",
    ),
)

WEB_SOURCES: tuple[ResearchSource, ...] = (
    FOOD_SOURCES[0],
    FOOD_SOURCES[1],
)



PRESET_SOURCES: dict[str, tuple[ResearchSource, ...]] = {
    "food": FOOD_SOURCES,
    "web": WEB_SOURCES,
}


def research_run_id() -> str:
    """Return the compact UTC timestamp used by research artifacts."""

    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_sites(sites: str | list[str] | tuple[str, ...] | None) -> list[str] | None:
    if sites is None:
        return None
    if isinstance(sites, str):
        values = sites.split(",")
    else:
        values = list(sites)
    normalized = [value.strip() for value in values if value.strip()]
    return normalized or None


def route_research(
    *,
    query: str,
    preset: str = "food",
    sites: str | list[str] | tuple[str, ...] | None = None,
    max_sites: int = 10,
) -> ResearchRoute:
    """Build source-specific browser jobs for a research query."""

    normalized_query = query.strip()
    if not normalized_query:
        raise BrowserConfigError("query must not be empty")
    if max_sites <= 0:
        raise BrowserConfigError("max_sites must be greater than 0")

    if preset not in PRESET_SOURCES:
        raise BrowserConfigError(
            f"Unknown research preset {preset!r}; supported presets: "
            + ", ".join(sorted(PRESET_SOURCES))
        )

    sources = list(PRESET_SOURCES[preset])
    selected_sites = _parse_sites(sites)
    if selected_sites:
        by_id = {source.source_id: source for source in sources}
        unknown = [site for site in selected_sites if site not in by_id]
        if unknown:
            raise BrowserConfigError(
                f"Unknown source id(s) for preset {preset!r}: {', '.join(unknown)}"
            )
        sources = [by_id[site] for site in selected_sites]

    encoded_query = quote(normalized_query, safe="")
    jobs = [
        ResearchJob(
            rank=index + 1,
            query=normalized_query,
            preset=preset,
            source_id=source.source_id,
            source_name=source.name,
            source_type=source.source_type,
            url=source.url_template.format(query=encoded_query),
            extraction_goal=(
                "Open the source search URL and capture visible result text, "
                "headings, links, and candidate cards for the outer agent to judge."
            ),
        )
        for index, source in enumerate(sources[:max_sites])
    ]
    return ResearchRoute(query=normalized_query, preset=preset, jobs=jobs)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object to a JSONL file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _event_payload(event_type: str, **payload: Any) -> dict[str, Any]:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
    }
    event.update(payload)
    return event


def _extract_page_data(
    *,
    connect_url: str,
    url: str,
    timeout_ms: float,
    wait_after_ms: float,
    max_chars: int,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception as exc:
        raise BrowserConfigError(
            "Failed to import Playwright. Install lex-browser-runtime[browser] "
            "or provide an environment that already includes playwright."
        ) from exc

    script = """
    ({ maxChars }) => {
      const clean = (value) => String(value || '').replace(/\\s+/g, ' ').trim();
      const absoluteHref = (element) => {
        const raw = element.getAttribute('href');
        if (!raw || raw.startsWith('javascript:')) return null;
        try { return new URL(raw, location.href).toString(); }
        catch { return raw; }
      };
      const links = Array.from(document.querySelectorAll('a'))
        .map((element) => ({ text: clean(element.innerText || element.textContent), href: absoluteHref(element) }))
        .filter((item) => item.text && item.href)
        .slice(0, 60);
      const headings = Array.from(document.querySelectorAll('h1,h2,h3,[role=heading]'))
        .map((element) => clean(element.innerText || element.textContent))
        .filter(Boolean)
        .slice(0, 30);
      const candidateSelector = [
        'article',
        '[role=listitem]',
        '[data-testid*=result]',
        '[class*=result]',
        '[class*=card]',
        '[class*=item]',
        'li'
      ].join(',');
      const seen = new Set();
      const candidates = Array.from(document.querySelectorAll(candidateSelector))
        .map((element) => {
          const text = clean(element.innerText || element.textContent);
          if (!text || text.length < 8 || seen.has(text)) return null;
          seen.add(text);
          const anchor = element.matches('a') ? element : element.querySelector('a');
          return { text: text.slice(0, 700), href: anchor ? absoluteHref(anchor) : null };
        })
        .filter(Boolean)
        .slice(0, 30);
      const bodyText = clean(document.body ? document.body.innerText : '');
      return {
        final_url: location.href,
        title: document.title || '',
        text: bodyText.slice(0, maxChars),
        headings,
        links,
        candidates
      };
    }
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(connect_url)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[-1] if context.pages else context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_after_ms:
                page.wait_for_timeout(wait_after_ms)
            payload = page.evaluate(
                script,
                {"maxChars": max_chars},
            )
            if not isinstance(payload, dict):
                raise BrowserRuntimeError(
                    "research page extraction returned non-object"
                )
            payload["status"] = response.status if response else None
            return payload
        finally:
            browser.close()


def _run_research_job(
    *,
    job: ResearchJob,
    admin_factory: Callable[[], LexmountBrowserAdmin],
    timeout_ms: float,
    wait_after_ms: float,
    max_chars: int,
    browser_mode: str,
    keep_sessions: bool,
    record_event: Callable[..., None] | None = None,
) -> ResearchJobResult:
    started_at = time.time()
    session_id: str | None = None
    inspect_url: str | None = None
    admin = admin_factory()
    try:
        session_result = admin.create_session(browser_mode=browser_mode)
        session = session_result.session
        session_id = session.session_id
        inspect_url = session.inspect_url or session.inspect_url_dbg
        if record_event is not None:
            record_event(
                "browser_created",
                source_id=job.source_id,
                source_name=job.source_name,
                url=job.url,
                session_id=session_id,
                inspect_url=inspect_url,
            )
        if not session.connect_url:
            raise BrowserRuntimeError(
                "Created research session did not expose connect_url"
            )
        extracted = _extract_page_data(
            connect_url=session.connect_url,
            url=job.url,
            timeout_ms=timeout_ms,
            wait_after_ms=wait_after_ms,
            max_chars=max_chars,
        )
        return ResearchJobResult(
            source_id=job.source_id,
            source_name=job.source_name,
            url=job.url,
            ok=True,
            duration_ms=(time.time() - started_at) * 1000,
            session_id=session_id,
            inspect_url=inspect_url,
            final_url=extracted.get("final_url"),
            title=extracted.get("title"),
            status=extracted.get("status"),
            text=extracted.get("text"),
            headings=[
                heading
                for heading in extracted.get("headings", [])
                if isinstance(heading, str)
            ],
            links=[
                ResearchLink.model_validate(link)
                for link in extracted.get("links", [])
                if isinstance(link, dict)
            ],
            candidates=[
                ResearchCandidate.model_validate(candidate)
                for candidate in extracted.get("candidates", [])
                if isinstance(candidate, dict)
            ],
        )
    except Exception as exc:
        return ResearchJobResult(
            source_id=job.source_id,
            source_name=job.source_name,
            url=job.url,
            ok=False,
            duration_ms=(time.time() - started_at) * 1000,
            session_id=session_id,
            inspect_url=inspect_url,
            error=exc.__class__.__name__,
            message=str(exc),
        )
    finally:
        if session_id and not keep_sessions:
            try:
                admin.close_session(session_id)
                if record_event is not None:
                    record_event(
                        "browser_closed",
                        source_id=job.source_id,
                        source_name=job.source_name,
                        url=job.url,
                        session_id=session_id,
                        inspect_url=inspect_url,
                    )
            except Exception:
                # The job result already carries the primary failure/success.
                # Cleanup failure should not hide page evidence from the caller.
                pass


def run_research(
    *,
    query: str,
    preset: str = "food",
    sites: str | list[str] | tuple[str, ...] | None = None,
    max_sites: int = 10,
    concurrency: int | None = None,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
    timeout_ms: float = 30000,
    wait_after_ms: float = 1000,
    max_chars: int = 6000,
    browser_mode: str = "normal",
    keep_sessions: bool = False,
    admin_factory: Callable[[], LexmountBrowserAdmin] = LexmountBrowserAdmin,
    job_runner: Callable[[ResearchJob], ResearchJobResult] | None = None,
    on_event: ResearchEventSink | None = None,
) -> ResearchRunSummary:
    """Run source jobs concurrently in separate Lexmount sessions."""

    resolved_concurrency = (
        concurrency if concurrency is not None else get_default_research_concurrency()
    )
    if resolved_concurrency <= 0:
        raise BrowserConfigError("concurrency must be greater than 0")
    if timeout_ms <= 0:
        raise BrowserConfigError("timeout_ms must be greater than 0")
    if max_chars <= 0:
        raise BrowserConfigError("max_chars must be greater than 0")

    route = route_research(
        query=query,
        preset=preset,
        sites=sites,
        max_sites=max_sites,
    )
    resolved_run_id = run_id or research_run_id()
    root = Path(output_dir) if output_dir else Path.cwd() / "lexmount-research-runs"
    resolved_output_dir = root / resolved_run_id
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    events_path = resolved_output_dir / "events.jsonl"
    sources_path = resolved_output_dir / "sources.jsonl"
    routes_path = resolved_output_dir / "routes.json"
    summary_path = resolved_output_dir / "summary.json"
    routes_path.write_text(
        route.model_dump_json(indent=2, by_alias=True) + "\n",
        encoding="utf-8",
    )

    lock = threading.Lock()

    def record_event(event_type: str, **payload: Any) -> None:
        event = _event_payload(event_type, **payload)
        with lock:
            _append_jsonl(events_path, event)
            if on_event is not None:
                on_event(event)

    record_event(
        "research_started",
        query=route.query,
        preset=route.preset,
        job_count=len(route.jobs),
        concurrency=resolved_concurrency,
    )

    def execute(job: ResearchJob) -> ResearchJobResult:
        record_event(
            "job_started",
            source_id=job.source_id,
            source_name=job.source_name,
            url=job.url,
        )
        if job_runner is not None:
            result = job_runner(job)
        else:
            result = _run_research_job(
                job=job,
                admin_factory=admin_factory,
                timeout_ms=timeout_ms,
                wait_after_ms=wait_after_ms,
                max_chars=max_chars,
                browser_mode=browser_mode,
                keep_sessions=keep_sessions,
                record_event=record_event,
            )
        record_event(
            "job_finished",
            source_id=job.source_id,
            source_name=job.source_name,
            ok=result.ok,
            duration_ms=result.duration_ms,
            error=result.error,
            message=result.message,
        )
        with lock:
            _append_jsonl(sources_path, result.model_dump(mode="json"))
        return result

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=resolved_concurrency,
    ) as executor:
        results = list(executor.map(execute, route.jobs))

    success_count = sum(1 for result in results if result.ok)
    failure_count = len(results) - success_count
    summary = ResearchRunSummary(
        ok=success_count > 0,
        query=route.query,
        preset=route.preset,
        run_id=resolved_run_id,
        output_dir=str(resolved_output_dir),
        events_path=str(events_path),
        sources_path=str(sources_path),
        routes_path=str(routes_path),
        summary_path=str(summary_path),
        success_count=success_count,
        failure_count=failure_count,
        concurrency=resolved_concurrency,
        jobs=route.jobs,
        results=results,
    )
    record_event(
        "research_finished",
        ok=summary.ok,
        success_count=success_count,
        failure_count=failure_count,
    )
    summary_path.write_text(
        summary.model_dump_json(indent=2, by_alias=True) + "\n",
        encoding="utf-8",
    )
    return summary


__all__ = [
    "ResearchCandidate",
    "ResearchJob",
    "ResearchJobResult",
    "ResearchLink",
    "ResearchRoute",
    "ResearchRunSummary",
    "ResearchSource",
    "research_run_id",
    "route_research",
    "run_research",
]
