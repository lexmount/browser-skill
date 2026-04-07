#!/usr/bin/env python3
"""Lexmount browser helper CLI for sessions, contexts, and browser actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict
from urllib.parse import quote_plus, urlsplit, urlunsplit


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SDK_SRC = REPO_ROOT / "lexmount-python-sdk" / "src"
SKILL_ENV = SCRIPT_DIR.parent / ".env"

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional convenience only
    load_dotenv = None

if load_dotenv and SKILL_ENV.exists():
    load_dotenv(SKILL_ENV, override=False)

if SDK_SRC.exists():
    sys.path.insert(0, str(SDK_SRC))

if TYPE_CHECKING:
    from lexmount import Lexmount
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright


REQUIRED_ENV_VARS = ("LEXMOUNT_API_KEY", "LEXMOUNT_PROJECT_ID")
DEFAULT_RUNS_ROOT = Path("/tmp/lexmount-runs")
ANSI_RESET = "\033[0m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_CYAN = "\033[36m"
TERMINAL_LOG_LOCK = threading.Lock()


def _missing_env_vars() -> list[str]:
    return [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]


def _json_dump(payload: Dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    raise SystemExit(exit_code)


def _print_research_terminal_summary(summary: dict[str, Any]) -> None:
    lines = [
        "",
        "=== Research Summary ===",
        "Downloaded HTML Files:",
    ]

    html_paths = summary.get("success_html_paths") or []
    if html_paths:
        for path in html_paths:
            lines.append(str(path))
    else:
        lines.append("(none)")
    lines.append("Summary JSON:")
    lines.append(f"  {summary.get('output_dir', '')}/summary.json")
    lines.append(f"Success Pages: {summary.get('success_count', 0)}")

    print("\n".join(lines))


def _terminal_log(message: str) -> None:
    with TERMINAL_LOG_LOCK:
        print(message, file=sys.stderr, flush=True)


def _current_research_success_count(results_lock: threading.Lock, consumed_results: list[dict[str, Any]]) -> int:
    with results_lock:
        return len(consumed_results)


def _success(command: str, **payload: Any) -> None:
    data = {"ok": True, "command": command}
    data.update(payload)
    _json_dump(data)


def _failure(command: str, error: str, message: str, *, exit_code: int = 1, **payload: Any) -> None:
    data = {
        "ok": False,
        "command": command,
        "error": error,
        "message": message,
    }
    data.update(payload)
    _json_dump(data, exit_code=exit_code)


def _load_sdk():
    try:
        from lexmount import Lexmount
        from lexmount.exceptions import LexmountError, ValidationError
    except Exception as exc:  # pragma: no cover - import failure path
        _failure(
            "sdk.load",
            "sdk_import_failed",
            (
                "Failed to import the lexmount SDK. Ensure the installed skill "
                "virtual environment has been bootstrapped with requirements.txt."
            ),
            details=str(exc),
            sdk_src=str(SDK_SRC),
        )

    return Lexmount, LexmountError, ValidationError


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - import failure path
        _failure(
            "playwright.load",
            "playwright_import_failed",
            "Failed to import Playwright. Ensure the current Python environment has playwright installed.",
            details=str(exc),
        )

    return sync_playwright


def _build_client() -> "Lexmount":
    Lexmount, _, ValidationError = _load_sdk()

    missing = _missing_env_vars()
    if missing:
        _failure(
            "client.build",
            "missing_env",
            "Missing required environment variables.",
            missing=missing,
        )

    try:
        return Lexmount()
    except ValidationError as exc:
        _failure(
            "client.build",
            "validation_error",
            str(exc),
        )


def _normalize_context_mode(value: str) -> str:
    if value not in {"read_write", "read_only"}:
        raise argparse.ArgumentTypeError("context mode must be read_write or read_only")
    return value


def _normalize_browser_mode(value: str) -> str:
    if value not in {"normal", "light", "chrome-light-docker"}:
        raise argparse.ArgumentTypeError("browser mode must be normal, light, or chrome-light-docker")
    return value


def _parse_metadata_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid metadata JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("metadata JSON must decode to an object")
    return value


def _serialize_session(session: Any) -> dict[str, Any]:
    return {
        "session_id": getattr(session, "id", None) or getattr(session, "session_id", None),
        "status": getattr(session, "status", None),
        "browser_mode": getattr(session, "browser_type", None),
        "project_id": getattr(session, "project_id", None),
        "created_at": getattr(session, "created_at", None),
        "inspect_url": getattr(session, "inspect_url", None),
        "inspect_url_dbg": getattr(session, "inspect_url_dbg", None),
        "container_id": getattr(session, "container_id", None),
        "connect_url": getattr(session, "connect_url", None) or getattr(session, "ws", None),
    }


def _serialize_context(item: Any) -> dict[str, Any]:
    return {
        "context_id": getattr(item, "id", None),
        "status": getattr(item, "status", None),
        "created_at": getattr(item, "created_at", None),
        "updated_at": getattr(item, "updated_at", None),
        "metadata": getattr(item, "metadata", None),
    }


def _handle_sdk_error(command: str, exc: Exception, **payload: Any) -> None:
    _failure(command, exc.__class__.__name__, str(exc), **payload)


def _resolve_session(client: "Lexmount", session_id: str) -> Any:
    sessions = client.sessions.list()
    for item in sessions:
        current_id = getattr(item, "id", None) or getattr(item, "session_id", None)
        if current_id == session_id:
            return item

    _failure(
        "session.get",
        "session_not_found",
        f"Session '{session_id}' was not found in sessions.list().",
        session_id=session_id,
    )


def _build_direct_connect_url() -> str:
    missing = _missing_env_vars()
    if missing:
        _failure(
            "direct-url",
            "missing_env",
            "Missing required environment variables.",
            missing=missing,
        )

    base_url = os.environ.get("LEXMOUNT_BASE_URL", "https://api.lexmount.cn").rstrip("/")
    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    return (
        f"{ws_base}/connection?project_id={os.environ['LEXMOUNT_PROJECT_ID']}"
        f"&api_key={os.environ['LEXMOUNT_API_KEY']}"
    )


def cmd_session_create(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        context_id = args.context_id
        created_context = False

        if args.create_context and not context_id:
            context = client.contexts.create(metadata=args.metadata)
            context_id = context.id
            created_context = True

        session_kwargs = {
            "browser_mode": args.browser_mode,
        }
        if context_id:
            session_kwargs["context"] = {"id": context_id, "mode": args.context_mode}

        session = client.sessions.create(**session_kwargs)

        _success(
            "session.create",
            mode="sdk",
            base_url=client.base_url,
            project_id=client.project_id,
            context_id=context_id,
            created_context=created_context,
            context_mode=args.context_mode,
            browser_mode=args.browser_mode,
            session=_serialize_session(session),
        )
    except LexmountError as exc:
        _handle_sdk_error("session.create", exc)


def cmd_session_list(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        result = client.sessions.list(status=args.status)
        sessions = [_serialize_session(item) for item in result]
        pagination = getattr(result, "pagination", None)
        _success(
            "session.list",
            count=len(sessions),
            status_filter=args.status,
            sessions=sessions,
            pagination={
                "current_page": getattr(pagination, "current_page", None),
                "page_size": getattr(pagination, "page_size", None),
                "total_count": getattr(pagination, "total_count", None),
                "total_pages": getattr(pagination, "total_pages", None),
                "active_count": getattr(pagination, "active_count", None),
                "closed_count": getattr(pagination, "closed_count", None),
            } if pagination else None,
        )
    except LexmountError as exc:
        _handle_sdk_error("session.list", exc)


def cmd_session_get(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        session = _resolve_session(client, args.session_id)
        _success("session.get", session=_serialize_session(session))
    except LexmountError as exc:
        _handle_sdk_error("session.get", exc, session_id=args.session_id)


def cmd_session_close(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        client.sessions.delete(session_id=args.session_id)
        _success(
            "session.close",
            session_id=args.session_id,
            closed=True,
        )
    except LexmountError as exc:
        _handle_sdk_error("session.close", exc, session_id=args.session_id)


def cmd_session_keepalive(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    started_at = time.time()
    snapshots: list[dict[str, Any]] = []
    deadline = started_at + args.duration if args.duration > 0 else None

    try:
        while True:
            session = _resolve_session(client, args.session_id)
            snapshot = {
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "session": _serialize_session(session),
            }
            snapshots.append(snapshot)

            if getattr(session, "status", None) != "active" and args.stop_on_inactive:
                break

            if deadline is not None and time.time() >= deadline:
                break

            time.sleep(args.interval)

        final_session = snapshots[-1]["session"] if snapshots else None
        _success(
            "session.keepalive",
            session_id=args.session_id,
            interval_seconds=args.interval,
            duration_seconds=args.duration,
            checks=len(snapshots),
            final_status=final_session.get("status") if final_session else None,
            snapshots=snapshots,
        )
    except LexmountError as exc:
        _handle_sdk_error("session.keepalive", exc, session_id=args.session_id)


def cmd_context_create(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        context = client.contexts.create(metadata=args.metadata)
        _success("context.create", context=_serialize_context(context))
    except LexmountError as exc:
        _handle_sdk_error("context.create", exc)


def cmd_context_list(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        result = client.contexts.list(status=args.status, limit=args.limit)
        contexts = [_serialize_context(item) for item in result]
        _success(
            "context.list",
            count=len(contexts),
            status_filter=args.status,
            limit=args.limit,
            contexts=contexts,
        )
    except LexmountError as exc:
        _handle_sdk_error("context.list", exc)


def cmd_context_get(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        context = client.contexts.get(args.context_id)
        _success("context.get", context=_serialize_context(context))
    except LexmountError as exc:
        _handle_sdk_error("context.get", exc, context_id=args.context_id)


def cmd_context_delete(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        client.contexts.delete(args.context_id)
        _success("context.delete", context_id=args.context_id, deleted=True)
    except LexmountError as exc:
        _handle_sdk_error("context.delete", exc, context_id=args.context_id)


def _connect_url_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "connect_url", None):
        return args.connect_url
    if getattr(args, "direct_url", False):
        return _build_direct_connect_url()
    if getattr(args, "session_id", None):
        client = _build_client()
        session = _resolve_session(client, args.session_id)
        connect_url = getattr(session, "connect_url", None) or getattr(session, "ws", None)
        if connect_url:
            return connect_url
        _failure(
            "action.resolve-connect-url",
            "missing_connect_url",
            f"Session '{args.session_id}' does not expose a connect URL in sessions.list().",
            session=_serialize_session(session),
        )

    _failure(
        "action.resolve-connect-url",
        "missing_target",
        "Pass one of --connect-url, --session-id, or --direct-url.",
    )


def _get_or_create_page(context: "BrowserContext") -> "Page":
    if context.pages:
        return context.pages[-1]
    return context.new_page()


def _case_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _runs_root() -> Path:
    root = Path(os.environ.get("LEXMOUNT_RUNS_ROOT", str(DEFAULT_RUNS_ROOT)))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_case_file(path: str) -> dict[str, Any]:
    case_path = Path(path)
    try:
        raw = case_path.read_text(encoding="utf-8")
    except OSError as exc:
        _failure("case.load", "case_read_failed", str(exc), path=str(case_path))

    suffix = case_path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            _failure("case.load", "case_parse_failed", f"Invalid JSON: {exc}", path=str(case_path))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except Exception as exc:  # pragma: no cover - optional dependency
            _failure(
                "case.load",
                "yaml_not_available",
                "PyYAML is required to load YAML case files.",
                details=str(exc),
                path=str(case_path),
            )
        try:
            data = yaml.safe_load(raw)
        except Exception as exc:
            _failure("case.load", "case_parse_failed", f"Invalid YAML: {exc}", path=str(case_path))
    else:
        _failure("case.load", "unsupported_case_format", "Case file must use .json, .yaml, or .yml", path=str(case_path))

    if not isinstance(data, dict):
        _failure("case.load", "invalid_case_root", "Case file root must be an object.", path=str(case_path))
    return data


def _run_index_path() -> Path:
    return _runs_root() / "index.jsonl"


def _append_run_index(entry: dict[str, Any]) -> None:
    index_path = _run_index_path()
    with index_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_run_index() -> list[dict[str, Any]]:
    path = _run_index_path()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            entries.append(item)
    return entries


def _append_event(log_path: Path, event_type: str, **payload: Any) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
    }
    event.update(payload)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_events(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _slugify(value: str, *, fallback: str = "item", max_length: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    if not slug:
        slug = fallback
    return slug[:max_length].strip("-") or fallback


def _normalize_web_url(raw: str) -> str | None:
    if not raw:
        return None
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def _research_engine_defaults(engine: str) -> dict[str, Any]:
    mapping = {
        "bing": {
            "search_url_template": "https://www.bing.com/search?q={query}&first={offset}",
            "result_selector": "li.b_algo h2 a",
            "offset_start": 1,
            "offset_step": 10,
        },
        "google": {
            "search_url_template": "https://www.google.com/search?q={query}&start={offset}",
            "result_selector": "div.yuRUbf > a",
            "offset_start": 0,
            "offset_step": 10,
        },
        "duckduckgo": {
            "search_url_template": "https://html.duckduckgo.com/html/?q={query}&s={offset}",
            "result_selector": "a.result__a",
            "offset_start": 0,
            "offset_step": 30,
        },
    }
    return mapping[engine]


def _research_output_dir(args: argparse.Namespace) -> tuple[str, Path]:
    run_id = args.run_id or f"research-{_case_now()}"
    output_dir = Path(args.output_dir) if args.output_dir else _runs_root() / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_id, output_dir


def _research_create_session(client: "Lexmount", *, browser_mode: str) -> dict[str, Any]:
    session = client.sessions.create(browser_mode=browser_mode)
    info = _serialize_session(session)
    connect_url = info.get("connect_url")
    if not connect_url:
        raise RuntimeError("created session did not expose connect_url")
    return info


def _research_close_sessions(client: "Lexmount", sessions: list[dict[str, Any]], event_log: Path) -> list[dict[str, Any]]:
    closed: list[dict[str, Any]] = []

    def close_one(session: dict[str, Any]) -> dict[str, Any] | None:
        session_id = session.get("session_id")
        if not session_id:
            return None
        try:
            client.sessions.delete(session_id=session_id)
            result = {"session_id": session_id, "closed": True}
            _append_event(event_log, "research_session_closed", session_id=session_id, ok=True)
            return result
        except Exception as exc:  # pragma: no cover - best effort cleanup
            result = {
                "session_id": session_id,
                "closed": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
            }
            _append_event(
                event_log,
                "research_session_closed",
                session_id=session_id,
                ok=False,
                error=exc.__class__.__name__,
                message=str(exc),
            )
            return result

    with ThreadPoolExecutor(max_workers=max(1, len(sessions))) as executor:
        futures = [executor.submit(close_one, session) for session in sessions]
        for future in as_completed(futures):
            result = future.result()
            if result:
                closed.append(result)

    closed.sort(key=lambda item: str(item.get("session_id") or ""))
    return closed


def _research_extract_links(page: "Page", selector: str) -> list[dict[str, Any]]:
    return page.eval_on_selector_all(
        selector,
        """
        (elements) => elements.map((el, index) => ({
          index,
          href: el.href || el.getAttribute('href') || '',
          text: (el.innerText || el.textContent || '').trim()
        }))
        """,
    )


def _research_wait_for_results(page: "Page", selector: str, timeout_ms: float) -> int:
    locator = page.locator(selector)
    deadline = time.time() + max(float(timeout_ms), 0.0) / 1000.0
    last_error: Exception | None = None

    while True:
        try:
            count = locator.count()
            if count > 0:
                try:
                    locator.first.wait_for(state="attached", timeout=500)
                except Exception as exc:  # pragma: no cover - best effort only
                    last_error = exc
                return count
        except Exception as exc:
            last_error = exc

        if time.time() >= deadline:
            break
        page.wait_for_timeout(250)

    raise TimeoutError(
        f"Timed out waiting for search results matching selector '{selector}'. "
        f"last_error={last_error.__class__.__name__ if last_error else None}: "
        f"{str(last_error) if last_error else 'no matching elements'}"
    )


def _research_try_extract_results(
    page: "Page",
    *,
    result_selector: str,
    timeout_ms: float,
) -> tuple[int, list[dict[str, Any]]]:
    extracted_count = _research_wait_for_results(page, result_selector, timeout_ms)
    extracted = _research_extract_links(page, result_selector)
    return max(len(extracted), extracted_count), extracted


def _research_load_search_results(
    page: "Page",
    *,
    search_url: str,
    result_selector: str,
    wait_until: str,
    timeout_ms: float,
) -> tuple[int, list[dict[str, Any]], dict[str, Any]]:
    timeout_ms = float(timeout_ms)
    metadata: dict[str, Any] = {
        "search_url": search_url,
        "attempts": [],
        "recovered_from_navigation_error": False,
    }

    try:
        page.goto(search_url, wait_until=wait_until, timeout=timeout_ms)
        count, extracted = _research_try_extract_results(page, result_selector=result_selector, timeout_ms=timeout_ms)
        metadata["attempts"].append(
            {
                "phase": "initial",
                "status": "ok",
                "timeout_ms": timeout_ms,
                "result_count": count,
            }
        )
        return count, extracted, metadata
    except Exception as exc:
        metadata["attempts"].append(
            {
                "phase": "initial",
                "status": "error",
                "timeout_ms": timeout_ms,
                "error": exc.__class__.__name__,
                "message": str(exc),
            }
        )

        try:
            count, extracted = _research_try_extract_results(page, result_selector=result_selector, timeout_ms=1500)
            metadata["recovered_from_navigation_error"] = True
            metadata["attempts"].append(
                {
                    "phase": "recover-current-dom",
                    "status": "ok",
                    "timeout_ms": 1500,
                    "result_count": count,
                }
            )
            return count, extracted, metadata
        except Exception as recover_exc:
            metadata["attempts"].append(
                {
                    "phase": "recover-current-dom",
                    "status": "error",
                    "timeout_ms": 1500,
                    "error": recover_exc.__class__.__name__,
                    "message": str(recover_exc),
                }
            )

        retry_timeout_ms = max(timeout_ms * 1.5, timeout_ms + 10000)
        page.wait_for_timeout(1500)
        try:
            page.goto(search_url, wait_until=wait_until, timeout=retry_timeout_ms)
            count, extracted = _research_try_extract_results(page, result_selector=result_selector, timeout_ms=retry_timeout_ms)
            metadata["attempts"].append(
                {
                    "phase": "retry",
                    "status": "ok",
                    "timeout_ms": retry_timeout_ms,
                    "result_count": count,
                }
            )
            return count, extracted, metadata
        except Exception as retry_exc:
            metadata["attempts"].append(
                {
                    "phase": "retry",
                    "status": "error",
                    "timeout_ms": retry_timeout_ms,
                    "error": retry_exc.__class__.__name__,
                    "message": str(retry_exc),
                }
            )
            raise RuntimeError(
                "Failed to load search results after initial attempt, DOM recovery, and one retry."
            ) from retry_exc


def _research_capture_page(
    page: "Page",
    item: dict[str, Any],
    output_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    rank = int(item["rank"])
    url = str(item["url"])
    slug_seed = item.get("title") or url
    slug = _slugify(str(slug_seed), fallback=f"page-{rank:03d}")
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    page_dir = output_root / "pages" / f"{rank:03d}-{slug}-{digest}"
    page_dir.mkdir(parents=True, exist_ok=True)

    started_at = time.time()
    response = page.goto(url, wait_until=args.page_wait_until, timeout=args.page_timeout_ms)
    page.wait_for_selector(args.content_selector, state=args.content_wait_state, timeout=args.page_timeout_ms)

    html = page.content()
    text = page.locator("body").inner_text(timeout=args.page_timeout_ms)
    if args.max_chars > 0:
        html = html[:args.max_chars]
        text = text[:args.max_chars]

    screenshot_path = None
    if args.screenshot:
        screenshot_path = page_dir / "page.png"
        page.screenshot(path=str(screenshot_path), full_page=True, timeout=args.page_timeout_ms)

    payload = {
        "rank": rank,
        "source": item,
        "url": url,
        "final_url": page.url,
        "title": page.title(),
        "status": response.status if response else None,
        "text": text,
        "html": html,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    html_path = page_dir / "page.html"
    html_path.write_text(payload["html"], encoding="utf-8")
    page_json = page_dir / "page.json"
    page_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "rank": rank,
        "url": url,
        "final_url": page.url,
        "title": payload["title"],
        "status": payload["status"],
        "artifact_dir": str(page_dir),
        "html_path": str(html_path),
        "page_json": str(page_json),
        "screenshot": str(screenshot_path) if screenshot_path else None,
        "duration_ms": round((time.time() - started_at) * 1000, 2),
        "text_chars": len(text),
        "html_chars": len(html),
    }


def cmd_research_knowledge(args: argparse.Namespace) -> None:
    run_id, output_dir = _research_output_dir(args)
    event_log = output_dir / "events.jsonl"
    links_log = output_dir / "links.jsonl"
    results_log = output_dir / "results.jsonl"

    if args.consumer_count < 1:
        _failure("research.knowledge", "invalid_consumer_count", "--consumer-count must be at least 1.")
    if args.max_links < 1:
        _failure("research.knowledge", "invalid_max_links", "--max-links must be at least 1.")
    if args.search_pages_max < 1:
        _failure("research.knowledge", "invalid_search_pages_max", "--search-pages-max must be at least 1.")
    if args.min_success_pages < 0:
        _failure("research.knowledge", "invalid_min_success_pages", "--min-success-pages must be at least 0.")

    defaults = _research_engine_defaults(args.search_engine)
    search_url_template = args.search_url_template or defaults["search_url_template"]
    result_selector = args.result_selector or defaults["result_selector"]
    offset_start = defaults["offset_start"]
    offset_step = args.page_size if args.page_size > 0 else defaults["offset_step"]

    client = _build_client()
    _, LexmountError, _ = _load_sdk()
    sync_playwright = _load_playwright()

    created_sessions: list[dict[str, Any]] = []
    closed_sessions: list[dict[str, Any]] = []
    producer_session: dict[str, Any] | None = None
    consumer_sessions: list[dict[str, Any]] = []

    produced_links: list[dict[str, Any]] = []
    consumed_results: list[dict[str, Any]] = []
    failed_results: list[dict[str, Any]] = []
    producer_failures: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    link_queue: queue.Queue[dict[str, Any] | None] = queue.Queue(maxsize=max(1, args.queue_size))
    results_lock = threading.Lock()

    _append_event(
        event_log,
        "research_started",
        run_id=run_id,
        query=args.query,
        max_links=args.max_links,
        consumer_count=args.consumer_count,
        search_engine=args.search_engine,
        output_dir=str(output_dir),
    )

    try:
        creation_jobs = [{"role": "producer", "browser_mode": args.producer_browser_mode}]
        for index in range(args.consumer_count):
            creation_jobs.append(
                {
                    "role": "consumer",
                    "consumer_index": index + 1,
                    "browser_mode": args.consumer_browser_mode,
                }
            )

        def create_session_job(job: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            session = _research_create_session(client, browser_mode=str(job["browser_mode"]))
            if job["role"] == "consumer":
                session["consumer_index"] = job["consumer_index"]
            return job, session

        with ThreadPoolExecutor(max_workers=max(1, len(creation_jobs))) as executor:
            future_map = {executor.submit(create_session_job, job): job for job in creation_jobs}
            for future in as_completed(future_map):
                job = future_map[future]
                try:
                    job_info, session = future.result()
                    created_sessions.append(session)
                    if job_info["role"] == "producer":
                        producer_session = session
                        _append_event(
                            event_log,
                            "research_session_created",
                            role="producer",
                            session=session,
                        )
                        _terminal_log(
                            f"[producer] session_created session={session.get('session_id')} "
                            f"browser_mode={job_info.get('browser_mode')}"
                        )
                    else:
                        consumer_sessions.append(session)
                        _append_event(
                            event_log,
                            "research_session_created",
                            role="consumer",
                            consumer_index=job_info["consumer_index"],
                            session=session,
                        )
                        _terminal_log(
                            f"[consumer-{job_info['consumer_index']}] session_created session={session.get('session_id')} "
                            f"browser_mode={job_info.get('browser_mode')}"
                        )
                except LexmountError as exc:
                    if job["role"] == "producer":
                        _handle_sdk_error("research.knowledge", exc, role="producer")
                    _append_event(
                        event_log,
                        "research_session_create_failed",
                        role=job["role"],
                        consumer_index=job.get("consumer_index"),
                        error=exc.__class__.__name__,
                        message=str(exc),
                    )
                except Exception as exc:
                    if job["role"] == "producer":
                        _failure(
                            "research.knowledge",
                            "producer_session_create_failed",
                            str(exc),
                            role="producer",
                        )
                    _append_event(
                        event_log,
                        "research_session_create_failed",
                        role=job["role"],
                        consumer_index=job.get("consumer_index"),
                        error=exc.__class__.__name__,
                        message=str(exc),
                    )

        if producer_session is None:
            _failure(
                "research.knowledge",
                "producer_session_create_failed",
                "Failed to create producer session.",
            )

        if not consumer_sessions:
            _failure(
                "research.knowledge",
                "no_consumer_sessions",
                "Failed to create any consumer sessions.",
                requested_consumer_count=args.consumer_count,
            )

        def consumer_worker(session_info: dict[str, Any]) -> None:
            consumer_index = int(session_info.get("consumer_index", 0))
            connect_url = str(session_info["connect_url"])
            _append_event(
                event_log,
                "consumer_started",
                consumer_index=consumer_index,
                session_id=session_info.get("session_id"),
            )
            _terminal_log(f"[consumer-{consumer_index}] started session={session_info.get('session_id')}")

            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(connect_url)
                try:
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    while True:
                        item = link_queue.get()
                        if item is None:
                            link_queue.task_done()
                            _append_event(event_log, "consumer_stopped", consumer_index=consumer_index)
                            _terminal_log(f"[consumer-{consumer_index}] stopped")
                            break

                        _append_event(
                            event_log,
                            "consumer_item_started",
                            consumer_index=consumer_index,
                            rank=item.get("rank"),
                            url=item.get("url"),
                        )
                        _terminal_log(
                            f"[consumer-{consumer_index}] consume rank={item.get('rank')} url={item.get('url')}"
                        )
                        page = context.new_page()
                        try:
                            result = _research_capture_page(page, item, output_dir, args)
                            result["ok"] = True
                            result["consumer_index"] = consumer_index
                            with results_lock:
                                consumed_results.append(result)
                            with results_log.open("a", encoding="utf-8") as fh:
                                fh.write(json.dumps(result, ensure_ascii=False) + "\n")
                            _append_event(
                                event_log,
                                "consumer_item_finished",
                                consumer_index=consumer_index,
                                rank=result.get("rank"),
                                url=result.get("url"),
                                ok=True,
                                duration_ms=result.get("duration_ms"),
                            )
                            _terminal_log(
                                f"[consumer-{consumer_index}] success rank={result.get('rank')} "
                                f"url={result.get('url')} html={result.get('html_path')}"
                            )
                        except Exception as exc:
                            failure = {
                                "ok": False,
                                "consumer_index": consumer_index,
                                "rank": item.get("rank"),
                                "url": item.get("url"),
                                "error": exc.__class__.__name__,
                                "message": str(exc),
                            }
                            with results_lock:
                                failed_results.append(failure)
                            with results_log.open("a", encoding="utf-8") as fh:
                                fh.write(json.dumps(failure, ensure_ascii=False) + "\n")
                            _append_event(
                                event_log,
                                "consumer_item_finished",
                                consumer_index=consumer_index,
                                rank=item.get("rank"),
                                url=item.get("url"),
                                ok=False,
                                error=exc.__class__.__name__,
                                message=str(exc),
                            )
                            _terminal_log(
                                f"[consumer-{consumer_index}] failed rank={item.get('rank')} "
                                f"url={item.get('url')} error={exc.__class__.__name__}: {exc}"
                            )
                        finally:
                            try:
                                page.close()
                            except Exception:
                                pass
                            link_queue.task_done()
                finally:
                    browser.close()

        workers = [
            threading.Thread(target=consumer_worker, args=(session_info,), daemon=True)
            for session_info in consumer_sessions
        ]
        for worker in workers:
            worker.start()

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(str(producer_session["connect_url"]))
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = _get_or_create_page(context)
                rank = 0

                for page_index in range(args.search_pages_max):
                    current_success_count = _current_research_success_count(results_lock, consumed_results)
                    if rank >= args.max_links and current_success_count >= args.min_success_pages:
                        break
                    if rank >= args.max_links and current_success_count < args.min_success_pages:
                        _terminal_log(
                            f"[producer] continue beyond max-links={args.max_links} "
                            f"because success_pages={current_success_count} < min_success_pages={args.min_success_pages}"
                        )

                    offset = offset_start + (page_index * offset_step)
                    search_url = search_url_template.format(
                        query=quote_plus(args.query),
                        offset=offset,
                        page=page_index + 1,
                    )
                    _append_event(
                        event_log,
                        "producer_page_started",
                        page_index=page_index + 1,
                        offset=offset,
                        search_url=search_url,
                    )

                    try:
                        extracted_count, extracted, load_meta = _research_load_search_results(
                            page,
                            search_url=search_url,
                            result_selector=result_selector,
                            wait_until=args.search_wait_until,
                            timeout_ms=args.search_timeout_ms,
                        )
                        _append_event(
                            event_log,
                            "producer_page_load_result",
                            page_index=page_index + 1,
                            offset=offset,
                            search_url=search_url,
                            recovered_from_navigation_error=load_meta.get("recovered_from_navigation_error"),
                            attempts=load_meta.get("attempts"),
                        )

                        accepted_on_page = 0
                        for entry in extracted:
                            normalized = _normalize_web_url(str(entry.get("href") or ""))
                            if not normalized or normalized in seen_urls:
                                continue

                            seen_urls.add(normalized)
                            rank += 1
                            accepted_on_page += 1
                            item = {
                                "rank": rank,
                                "url": normalized,
                                "title": str(entry.get("text") or "").strip(),
                                "search_page": page_index + 1,
                                "search_offset": offset,
                                "search_url": search_url,
                            }
                            produced_links.append(item)
                            with links_log.open("a", encoding="utf-8") as fh:
                                fh.write(json.dumps(item, ensure_ascii=False) + "\n")
                            _append_event(
                                event_log,
                                "producer_link_enqueued",
                                rank=rank,
                                url=normalized,
                                search_page=page_index + 1,
                            )
                            _terminal_log(
                                f"[producer] enqueue rank={rank} page={page_index + 1} url={normalized}"
                            )
                            link_queue.put(item)
                            current_success_count = _current_research_success_count(results_lock, consumed_results)
                            if rank >= args.max_links and current_success_count >= args.min_success_pages:
                                break

                        _append_event(
                            event_log,
                            "producer_page_finished",
                            page_index=page_index + 1,
                            offset=offset,
                            extracted_count=max(len(extracted), extracted_count),
                            accepted_count=accepted_on_page,
                            total_produced=rank,
                        )

                        if accepted_on_page == 0 and not extracted:
                            current_success_count = _current_research_success_count(results_lock, consumed_results)
                            _append_event(
                                event_log,
                                "producer_page_empty",
                                page_index=page_index + 1,
                                offset=offset,
                                search_url=search_url,
                                success_pages=current_success_count,
                                min_success_pages=args.min_success_pages,
                            )
                            if current_success_count >= args.min_success_pages:
                                break
                            _terminal_log(
                                f"[producer] page_empty page={page_index + 1} but continuing because "
                                f"success_pages={current_success_count} < min_success_pages={args.min_success_pages}"
                            )
                            continue
                    except Exception as exc:
                        failure = {
                            "page_index": page_index + 1,
                            "offset": offset,
                            "search_url": search_url,
                            "error": exc.__class__.__name__,
                            "message": str(exc),
                        }
                        producer_failures.append(failure)
                        _append_event(
                            event_log,
                            "producer_page_failed",
                            page_index=page_index + 1,
                            offset=offset,
                            search_url=search_url,
                            error=exc.__class__.__name__,
                            message=str(exc),
                        )
                        _terminal_log(
                            f"[producer] page_failed page={page_index + 1} search_url={search_url} "
                            f"error={exc.__class__.__name__}: {exc}"
                        )
                        continue
            finally:
                browser.close()

        for _ in consumer_sessions:
            link_queue.put(None)
        link_queue.join()
        for worker in workers:
            worker.join()

        consumed_results.sort(key=lambda item: int(item.get("rank", 0)))
        failed_results.sort(key=lambda item: int(item.get("rank", 0) or 0))

        total_visited_count = len(consumed_results) + len(failed_results)
        success_html_paths = [item["html_path"] for item in consumed_results if item.get("html_path")]
        success_storage = [
            {
                "rank": item.get("rank"),
                "url": item.get("url"),
                "html_path": item.get("html_path"),
                "page_json": item.get("page_json"),
            }
            for item in consumed_results
            if item.get("html_path")
        ]

        summary = {
            "ok": len(produced_links) > 0 and len(failed_results) == 0,
            "command": "research.knowledge",
            "run_id": run_id,
            "query": args.query,
            "search_engine": args.search_engine,
            "search_url_template": search_url_template,
            "result_selector": result_selector,
            "output_dir": str(output_dir),
            "events_path": str(event_log),
            "links_path": str(links_log),
            "results_path": str(results_log),
            "producer_session": producer_session,
            "consumer_sessions": consumer_sessions,
            "produced_count": len(produced_links),
            "visited_count": total_visited_count,
            "success_count": len(consumed_results),
            "failure_count": len(failed_results),
            "consumed_count": len(consumed_results),
            "failed_count": len(failed_results),
            "producer_failed_count": len(producer_failures),
            "requested_max_links": args.max_links,
            "requested_consumer_count": args.consumer_count,
            "actual_consumer_count": len(consumer_sessions),
            "success_html_paths": success_html_paths,
            "success_storage": success_storage,
            "produced_links": produced_links,
            "consumed_results": consumed_results,
            "failed_results": failed_results,
            "producer_failures": producer_failures,
        }
        (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        _append_event(
            event_log,
            "research_finished",
            ok=summary["ok"],
            produced_count=summary["produced_count"],
            consumed_count=summary["consumed_count"],
            failed_count=summary["failed_count"],
            producer_failed_count=summary["producer_failed_count"],
        )
    finally:
        if created_sessions and not args.keep_sessions:
            closed_sessions = _research_close_sessions(client, created_sessions, event_log)
            summary_path = output_dir / "summary.json"
            if summary_path.exists():
                summary = _load_summary_file(summary_path) or {}
                if summary:
                    summary["session_cleanup"] = closed_sessions
                    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = _load_summary_file(output_dir / "summary.json")
    if not summary:
        _failure(
            "research.knowledge",
            "summary_missing",
            "Research run finished without producing summary.json.",
            output_dir=str(output_dir),
        )
    _print_research_terminal_summary(summary)
    raise SystemExit(0 if summary.get("ok") else 1)


def _validate_case_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty array")
        return errors

    supported_actions = {
        "open-url",
        "wait-selector",
        "click",
        "type",
        "screenshot",
        "eval",
        "snapshot",
    }
    required_fields = {
        "open-url": ("url",),
        "wait-selector": ("selector",),
        "click": ("selector",),
        "type": ("selector", "text"),
        "screenshot": tuple(),
        "eval": ("expression",),
        "snapshot": tuple(),
    }

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue
        action = step.get("action")
        if action not in supported_actions:
            errors.append(f"steps[{index}].action must be one of {sorted(supported_actions)}")
            continue
        for field in required_fields[action]:
            if field not in step:
                errors.append(f"steps[{index}] missing required field '{field}'")

    if "target" in spec and not isinstance(spec["target"], dict):
        errors.append("target must be an object when present")
    if "session" in spec and not isinstance(spec["session"], dict):
        errors.append("session must be an object when present")

    return errors


def _case_connect_target(client: "Lexmount", spec: dict[str, Any]) -> tuple[str, dict[str, Any] | None, bool]:
    target = spec.get("target") or {}
    session_spec = spec.get("session") or {}

    if not isinstance(target, dict):
        target = {}
    if not isinstance(session_spec, dict):
        session_spec = {}

    created_session = False
    created_session_info: dict[str, Any] | None = None

    if session_spec.get("create"):
        context_id = session_spec.get("context_id")
        created_context = False
        metadata = session_spec.get("metadata")
        if session_spec.get("create_context") and not context_id:
            context = client.contexts.create(metadata=metadata)
            context_id = context.id
            created_context = True

        session_kwargs = {
            "browser_mode": session_spec.get("browser_mode", "normal"),
        }
        context_mode = session_spec.get("context_mode", "read_write")
        if context_id:
            session_kwargs["context"] = {"id": context_id, "mode": context_mode}

        session = client.sessions.create(**session_kwargs)
        created_session = True
        created_session_info = _serialize_session(session)
        created_session_info["created_context"] = created_context
        created_session_info["context_id"] = context_id
        return session.connect_url, created_session_info, created_session

    if target.get("connect_url"):
        return str(target["connect_url"]), created_session_info, created_session
    if target.get("direct_url"):
        return _build_direct_connect_url(), created_session_info, created_session
    if target.get("session_id"):
        session = _resolve_session(client, str(target["session_id"]))
        connect_url = getattr(session, "connect_url", None) or getattr(session, "ws", None)
        if not connect_url:
            _failure(
                "case.resolve-target",
                "missing_connect_url",
                "Resolved session does not expose connect_url.",
                session=_serialize_session(session),
            )
        return connect_url, _serialize_session(session), created_session

    _failure(
        "case.resolve-target",
        "missing_target",
        "Case file must provide target.connect_url, target.session_id, target.direct_url, or session.create=true.",
    )


def _case_step_output_path(step: dict[str, Any], artifacts_dir: Path, index: int) -> str:
    output = step.get("output")
    if output:
        output_path = Path(str(output))
        if not output_path.is_absolute():
            output_path = artifacts_dir / output_path
    else:
        output_path = artifacts_dir / f"step-{index:02d}-screenshot.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return str(output_path)


def _run_case_step(page: "Page", step: dict[str, Any], artifacts_dir: Path, index: int) -> dict[str, Any]:
    action = step["action"]
    timeout_ms = step.get("timeout_ms", 30000)

    if action == "open-url":
        response = page.goto(step["url"], wait_until=step.get("wait_until", "load"), timeout=timeout_ms)
        return {
            "url": page.url,
            "title": page.title(),
            "status": response.status if response else None,
        }
    if action == "wait-selector":
        locator = page.wait_for_selector(step["selector"], state=step.get("state", "visible"), timeout=timeout_ms)
        return {
            "selector": step["selector"],
            "state": step.get("state", "visible"),
            "text": locator.text_content() if locator else None,
            "url": page.url,
        }
    if action == "click":
        page.click(step["selector"], timeout=timeout_ms)
        if step.get("wait_after_ms"):
            page.wait_for_timeout(step["wait_after_ms"])
        return {"selector": step["selector"], "clicked": True, "url": page.url}
    if action == "type":
        page.fill(step["selector"], step["text"], timeout=timeout_ms)
        if step.get("press_enter"):
            page.press(step["selector"], "Enter", timeout=timeout_ms)
        return {
            "selector": step["selector"],
            "typed": True,
            "press_enter": bool(step.get("press_enter")),
            "url": page.url,
        }
    if action == "screenshot":
        output_path = _case_step_output_path(step, artifacts_dir, index)
        page.screenshot(path=output_path, full_page=bool(step.get("full_page")), timeout=timeout_ms)
        return {"path": output_path, "full_page": bool(step.get("full_page")), "url": page.url}
    if action == "eval":
        value = page.evaluate(step["expression"])
        return {"expression": step["expression"], "value": value, "url": page.url}
    if action == "snapshot":
        max_chars = int(step.get("max_chars", 8000))
        html = page.content()
        text = page.locator("body").inner_text(timeout=timeout_ms)
        if max_chars > 0:
            html = html[:max_chars]
            text = text[:max_chars]
        snapshot_path = step.get("output")
        if snapshot_path:
            output_path = _case_step_output_path(step, artifacts_dir, index)
            Path(output_path).write_text(
                json.dumps({"html": html, "text": text, "url": page.url, "title": page.title()}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return {"url": page.url, "title": page.title(), "html": html, "text": text}

    raise ValueError(f"Unsupported action: {action}")


def _run_action(
    args: argparse.Namespace,
    command: str,
    action: Callable[["Page"], dict[str, Any]],
) -> None:
    connect_url = _connect_url_from_args(args)
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(connect_url)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = _get_or_create_page(context)
            result = action(page)
            _success(
                command,
                session_id=getattr(args, "session_id", None),
                connect_url=connect_url,
                result=result,
            )
        finally:
            browser.close()


def cmd_action_open_url(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        response = page.goto(args.url, wait_until=args.wait_until, timeout=args.timeout_ms)
        return {
            "url": page.url,
            "title": page.title(),
            "status": response.status if response else None,
        }

    _run_action(args, "action.open-url", action)


def cmd_action_wait_selector(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        locator = page.wait_for_selector(args.selector, state=args.state, timeout=args.timeout_ms)
        return {
            "url": page.url,
            "selector": args.selector,
            "state": args.state,
            "text": locator.text_content() if locator else None,
        }

    _run_action(args, "action.wait-selector", action)


def cmd_action_click(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        page.click(args.selector, timeout=args.timeout_ms)
        if args.wait_after_ms:
            page.wait_for_timeout(args.wait_after_ms)
        return {
            "url": page.url,
            "selector": args.selector,
            "clicked": True,
        }

    _run_action(args, "action.click", action)


def cmd_action_type(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        page.fill(args.selector, args.text, timeout=args.timeout_ms)
        if args.press_enter:
            page.press(args.selector, "Enter", timeout=args.timeout_ms)
        return {
            "url": page.url,
            "selector": args.selector,
            "typed": True,
            "press_enter": args.press_enter,
        }

    _run_action(args, "action.type", action)


def cmd_action_screenshot(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        output_path = args.output or str((Path("/tmp") / f"lexmount-screenshot-{int(time.time())}.png"))
        page.screenshot(path=output_path, full_page=args.full_page, timeout=args.timeout_ms)
        return {
            "url": page.url,
            "path": output_path,
            "full_page": args.full_page,
        }

    _run_action(args, "action.screenshot", action)


def cmd_action_eval(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        value = page.evaluate(args.expression)
        return {
            "url": page.url,
            "expression": args.expression,
            "value": value,
        }

    _run_action(args, "action.eval", action)


def cmd_action_snapshot(args: argparse.Namespace) -> None:
    def action(page: "Page") -> dict[str, Any]:
        html = page.content()
        body_text = page.locator("body").inner_text(timeout=args.timeout_ms)
        if args.max_chars > 0:
            html = html[:args.max_chars]
            body_text = body_text[:args.max_chars]
        return {
            "url": page.url,
            "title": page.title(),
            "html": html,
            "text": body_text,
        }

    _run_action(args, "action.snapshot", action)


def cmd_direct_url(args: argparse.Namespace) -> None:
    _success(
        "direct-url",
        mode="direct",
        connect_url=_build_direct_connect_url(),
    )


def cmd_prepare(args: argparse.Namespace) -> None:
    cmd_session_create(args)


def cmd_list_contexts(args: argparse.Namespace) -> None:
    cmd_context_list(args)


def cmd_close_session(args: argparse.Namespace) -> None:
    cmd_session_close(args)


def cmd_case_validate(args: argparse.Namespace) -> None:
    spec = _load_case_file(args.file)
    errors = _validate_case_spec(spec)
    _success(
        "case.validate",
        file=args.file,
        valid=not errors,
        errors=errors,
        step_count=len(spec.get("steps", [])) if isinstance(spec.get("steps"), list) else 0,
    )


def cmd_case_run(args: argparse.Namespace) -> None:
    spec = _load_case_file(args.file)
    errors = _validate_case_spec(spec)
    if errors:
        _failure("case.run", "invalid_case", "Case validation failed.", errors=errors, file=args.file)

    client = _build_client()
    connect_url, session_info, created_session = _case_connect_target(client, spec)
    run_id = getattr(args, "run_id", None) or spec.get("run_id") or f"case-{_case_now()}-{time.time_ns()}"
    artifacts_dir = Path(args.artifacts_dir or f"/tmp/lexmount-runs/{run_id}")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    event_log = artifacts_dir / "events.jsonl"
    _append_event(event_log, "case_started", run_id=run_id, file=args.file, artifacts_dir=str(artifacts_dir))
    _append_event(
        event_log,
        "session_resolved",
        run_id=run_id,
        created_session=created_session,
        session=session_info,
        connect_url=connect_url,
    )

    sync_playwright = _load_playwright()
    results: list[dict[str, Any]] = []
    created_session_id = session_info.get("session_id") if session_info else None

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(connect_url)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = _get_or_create_page(context)
            for index, step in enumerate(spec["steps"]):
                started_at = time.time()
                _append_event(
                    event_log,
                    "step_started",
                    run_id=run_id,
                    index=index,
                    action=step.get("action"),
                    step=step,
                )
                try:
                    result = _run_case_step(page, step, artifacts_dir, index)
                    duration_ms = round((time.time() - started_at) * 1000, 2)
                    results.append(
                        {
                            "index": index,
                            "action": step["action"],
                            "ok": True,
                            "duration_ms": duration_ms,
                            "result": result,
                        }
                    )
                    _append_event(
                        event_log,
                        "step_finished",
                        run_id=run_id,
                        index=index,
                        action=step["action"],
                        ok=True,
                        duration_ms=duration_ms,
                        result=result,
                    )
                except Exception as exc:
                    duration_ms = round((time.time() - started_at) * 1000, 2)
                    results.append(
                        {
                            "index": index,
                            "action": step.get("action"),
                            "ok": False,
                            "duration_ms": duration_ms,
                            "error": exc.__class__.__name__,
                            "message": str(exc),
                        }
                    )
                    _append_event(
                        event_log,
                        "step_finished",
                        run_id=run_id,
                        index=index,
                        action=step.get("action"),
                        ok=False,
                        duration_ms=duration_ms,
                        error=exc.__class__.__name__,
                        message=str(exc),
                    )
                    if args.stop_on_error:
                        break
        finally:
            browser.close()
            _append_event(event_log, "browser_closed", run_id=run_id)

    if created_session and created_session_id and (args.close_created_session or spec.get("close_created_session")):
        try:
            client.sessions.delete(session_id=created_session_id)
            session_info["closed_after_run"] = True
            _append_event(event_log, "session_closed", run_id=run_id, session_id=created_session_id, ok=True)
        except Exception as exc:  # pragma: no cover - best effort cleanup
            session_info["close_after_run_error"] = str(exc)
            _append_event(
                event_log,
                "session_closed",
                run_id=run_id,
                session_id=created_session_id,
                ok=False,
                error=exc.__class__.__name__,
                message=str(exc),
            )

    summary = {
        "ok": all(item["ok"] for item in results),
        "command": "case.run",
        "file": args.file,
        "run_id": run_id,
        "artifacts_dir": str(artifacts_dir),
        "events_path": str(event_log),
        "connect_url": connect_url,
        "session": session_info,
        "steps": results,
    }
    (artifacts_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_event(
        event_log,
        "case_finished",
        run_id=run_id,
        ok=summary["ok"],
        steps_total=len(results),
        steps_ok=sum(1 for item in results if item["ok"]),
        steps_failed=sum(1 for item in results if not item["ok"]),
    )
    _json_dump(summary, exit_code=0 if summary["ok"] else 1)


def _load_summary_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _collect_batch_summaries(batch_dir: Path) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    if not batch_dir.exists():
        return summaries
    for summary_path in sorted(batch_dir.glob("run-*/summary.json")):
        data = _load_summary_file(summary_path)
        if data:
            summaries.append(data)
    return summaries


def _resolve_batch_dir(batch_id: str | None, batch_dir: str | None, *, command: str) -> tuple[str, Path]:
    if batch_id:
        return batch_id, _runs_root() / batch_id
    if batch_dir:
        path = Path(batch_dir)
        return path.name, path
    _failure(command, "missing_target", "Pass --batch-id or --batch-dir.")


def _make_batch_summary(batch_id: str, batch_dir: Path, file: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    ok_count = sum(1 for item in summaries if item.get("ok"))
    failed_count = len(summaries) - ok_count
    return {
        "ok": failed_count == 0,
        "command": "run.submit",
        "batch_id": batch_id,
        "file": file,
        "batch_dir": str(batch_dir),
        "events_path": str(batch_dir / "events.jsonl"),
        "count": len(summaries),
        "ok_count": ok_count,
        "failed_count": failed_count,
        "runs": [
            {
                "run_id": item.get("run_id"),
                "ok": item.get("ok"),
                "artifacts_dir": item.get("artifacts_dir"),
                "session_id": (item.get("session") or {}).get("session_id"),
            }
            for item in summaries
        ],
    }


def _collect_run_watch_state(batch_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for run_dir in sorted(batch_dir.glob("run-*")):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        events = _read_events(run_dir / "events.jsonl")
        summary = _load_summary_file(run_dir / "summary.json")
        state: dict[str, Any] = {
            "run_dir": str(run_dir),
            "run_id": summary.get("run_id") if summary else run_id,
            "session_id": (summary.get("session") or {}).get("session_id") if summary else None,
            "status": "unknown",
            "current_step": None,
            "last_event_type": events[-1].get("type") if events else None,
            "last_event_at": events[-1].get("timestamp") if events else None,
        }
        if summary:
            state["ok"] = summary.get("ok")
            state["status"] = "passed" if summary.get("ok") else "failed"
        if events:
            current_step = None
            for event in events:
                if event.get("type") == "step_started":
                    current_step = {
                        "index": event.get("index"),
                        "action": event.get("action"),
                        "started_at": event.get("timestamp"),
                    }
                elif event.get("type") == "step_finished":
                    current_step = None

            last = events[-1]
            last_type = last.get("type")
            if last_type == "case_finished":
                state["status"] = "passed" if last.get("ok") else "failed"
            elif last_type == "session_closed":
                state["status"] = "closing"
            elif last_type in {"step_started", "step_finished", "session_resolved", "browser_closed"}:
                state["status"] = "running"
            elif last_type == "case_started":
                state["status"] = "starting"

            if current_step is not None:
                state["current_step"] = current_step

            for event in reversed(events):
                if event.get("type") == "step_finished" and not event.get("ok", True):
                    state["failure"] = {
                        "index": event.get("index"),
                        "action": event.get("action"),
                        "error": event.get("error"),
                        "message": event.get("message"),
                    }
                    break

        if summary:
            steps = summary.get("steps") or []
            state["steps_total"] = len(steps)
            state["steps_ok"] = sum(1 for item in steps if item.get("ok"))
            state["steps_failed"] = sum(1 for item in steps if not item.get("ok"))
        runs.append(state)
    return runs


def _build_watch_snapshot(batch_dir: Path) -> dict[str, Any]:
    summaries = _collect_batch_summaries(batch_dir)
    batch_events = _read_events(batch_dir / "events.jsonl")
    runs = _collect_run_watch_state(batch_dir)
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "batch_dir": str(batch_dir),
        "batch_events": len(batch_events),
        "completed_runs": len(summaries),
        "ok_runs": sum(1 for item in summaries if item.get("ok")),
        "failed_runs": sum(1 for item in summaries if not item.get("ok")),
        "submitted_runs": sum(1 for event in batch_events if event.get("type") in {"run_submitted", "retry_run_submitted"}),
        "last_batch_event_type": batch_events[-1].get("type") if batch_events else None,
        "last_batch_event_at": batch_events[-1].get("timestamp") if batch_events else None,
        "runs": runs,
    }


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _colorize(text: str, color: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{color}{text}{ANSI_RESET}"


def _status_badge(status: str, *, enabled: bool) -> str:
    mapping = {
        "passed": ("OK", ANSI_GREEN),
        "failed": ("FAIL", ANSI_RED),
        "running": ("RUN", ANSI_BLUE),
        "starting": ("START", ANSI_CYAN),
        "closing": ("CLOSE", ANSI_YELLOW),
        "unknown": ("?", ANSI_YELLOW),
    }
    label, color = mapping.get(status, (status.upper(), ANSI_YELLOW))
    return _colorize(label, color, enabled=enabled)


def _format_live_snapshot(snapshot: dict[str, Any]) -> str:
    colors = _supports_color()
    lines = [
        (
            f"[{snapshot.get('checked_at')}] completed={snapshot.get('completed_runs', 0)} "
            f"ok={_colorize(str(snapshot.get('ok_runs', 0)), ANSI_GREEN, enabled=colors)} "
            f"failed={_colorize(str(snapshot.get('failed_runs', 0)), ANSI_RED, enabled=colors)} "
            f"submitted={snapshot.get('submitted_runs', 0)} "
            f"last_batch_event={snapshot.get('last_batch_event_type') or '-'}"
        )
    ]
    for run in snapshot.get("runs", []):
        line = f"[{_status_badge(run.get('status', 'unknown'), enabled=colors)}] {run.get('run_id')}"
        if run.get("current_step"):
            step = run["current_step"]
            line += f" step={step.get('index')}:{step.get('action')}"
        if run.get("failure"):
            failure = run["failure"]
            line += f" failure={failure.get('action')}:{failure.get('error')}"
        if run.get("session_id"):
            line += f" session={run.get('session_id')}"
        lines.append(line)
    return "\n".join(lines)


def _write_batch_summary(batch_dir: Path, batch_summary: dict[str, Any]) -> None:
    (batch_dir / "batch-summary.json").write_text(
        json.dumps(batch_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_case_subprocess(
    *,
    file: str,
    run_id: str,
    artifacts_dir: Path,
    stop_on_error: bool,
    close_created_session: bool,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "case",
        "run",
        "--file",
        file,
        "--run-id",
        run_id,
        "--artifacts-dir",
        str(artifacts_dir),
    ]
    if stop_on_error:
        cmd.append("--stop-on-error")
    if close_created_session:
        cmd.append("--close-created-session")

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "command": "case.run",
            "error": "invalid_subprocess_output",
            "message": proc.stdout.strip() or proc.stderr.strip() or "case subprocess did not emit JSON",
        }

    if not isinstance(payload, dict):
        payload = {
            "ok": False,
            "command": "case.run",
            "error": "invalid_subprocess_output",
            "message": "case subprocess did not emit an object",
        }

    payload.setdefault("artifacts_dir", str(artifacts_dir))
    payload["_returncode"] = proc.returncode
    if proc.stderr.strip():
        payload["_stderr"] = proc.stderr.strip()
    return payload


def cmd_run_submit(args: argparse.Namespace) -> None:
    spec = _load_case_file(args.file)
    errors = _validate_case_spec(spec)
    if errors:
        _failure("run.submit", "invalid_case", "Case validation failed.", errors=errors, file=args.file)

    batch_id = args.batch_id or f"batch-{_case_now()}"
    batch_dir = _runs_root() / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_event_log = batch_dir / "events.jsonl"
    _append_event(
        batch_event_log,
        "batch_started",
        batch_id=batch_id,
        file=args.file,
        count=args.count,
        concurrency=args.concurrency,
    )

    jobs = []
    for index in range(args.count):
        jobs.append(
            {
                "run_id": f"{batch_id}-run-{index + 1:03d}",
                "artifacts_dir": batch_dir / f"run-{index + 1:03d}",
            }
        )

    summaries: list[dict[str, Any]] = []

    def worker(job: dict[str, Any]) -> dict[str, Any]:
        _append_event(
            batch_event_log,
            "run_submitted",
            batch_id=batch_id,
            run_id=job["run_id"],
            artifacts_dir=str(job["artifacts_dir"]),
        )
        payload = _run_case_subprocess(
            file=args.file,
            run_id=job["run_id"],
            artifacts_dir=job["artifacts_dir"],
            stop_on_error=args.stop_on_error,
            close_created_session=args.close_created_session,
        )
        payload.setdefault("run_id", job["run_id"])
        return payload

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        future_map = {executor.submit(worker, job): job for job in jobs}
        for future in as_completed(future_map):
            job = future_map[future]
            try:
                payload = future.result()
            except Exception as exc:
                payload = {
                    "ok": False,
                    "command": "case.run",
                    "run_id": job["run_id"],
                    "artifacts_dir": str(job["artifacts_dir"]),
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                }
            payload.setdefault("run_id", job["run_id"])
            payload.setdefault("artifacts_dir", str(job["artifacts_dir"]))
            summaries.append(payload)
            _append_event(
                batch_event_log,
                "run_completed",
                batch_id=batch_id,
                run_id=payload.get("run_id"),
                ok=payload.get("ok"),
                artifacts_dir=payload.get("artifacts_dir"),
                session_id=(payload.get("session") or {}).get("session_id"),
            )

    summaries.sort(key=lambda item: item.get("run_id", ""))
    batch_summary = _make_batch_summary(batch_id, batch_dir, args.file, summaries)
    _write_batch_summary(batch_dir, batch_summary)
    _append_run_index(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "batch_id": batch_id,
            "file": args.file,
            "batch_dir": str(batch_dir),
            "count": batch_summary["count"],
            "ok_count": batch_summary["ok_count"],
            "failed_count": batch_summary["failed_count"],
        }
    )
    _append_event(
        batch_event_log,
        "batch_finished",
        batch_id=batch_id,
        ok=batch_summary["ok"],
        count=batch_summary["count"],
        ok_count=batch_summary["ok_count"],
        failed_count=batch_summary["failed_count"],
    )
    _json_dump(batch_summary, exit_code=0 if batch_summary["ok"] else 1)


def cmd_run_list(args: argparse.Namespace) -> None:
    entries = _read_run_index()
    if args.limit > 0:
        entries = entries[-args.limit :]
    entries = list(reversed(entries))
    _success(
        "run.list",
        count=len(entries),
        runs=entries,
        runs_root=str(_runs_root()),
    )


def cmd_run_summary(args: argparse.Namespace) -> None:
    _, batch_dir = _resolve_batch_dir(args.batch_id, args.batch_dir, command="run.summary")

    batch_summary_path = batch_dir / "batch-summary.json"
    if batch_summary_path.exists():
        summary = _load_summary_file(batch_summary_path)
        if summary:
            _json_dump(summary, exit_code=0 if summary.get("ok") else 1)

    summaries = _collect_batch_summaries(batch_dir)
    if not summaries:
        _failure("run.summary", "batch_not_found", "No run summaries were found for the requested batch.", batch_dir=str(batch_dir))

    batch_id = args.batch_id or batch_dir.name
    batch_summary = _make_batch_summary(batch_id, batch_dir, summaries[0].get("file", ""), summaries)
    _write_batch_summary(batch_dir, batch_summary)
    _json_dump(batch_summary, exit_code=0 if batch_summary["ok"] else 1)


def cmd_run_watch(args: argparse.Namespace) -> None:
    _, batch_dir = _resolve_batch_dir(args.batch_id, args.batch_dir, command="run.watch")

    started = time.time()
    snapshots: list[dict[str, Any]] = []
    last_rendered: str | None = None
    while True:
        snapshot = _build_watch_snapshot(batch_dir)
        snapshots.append(snapshot)

        if args.live:
            rendered = _format_live_snapshot(snapshot)
            if not args.changes_only or rendered != last_rendered:
                if last_rendered is not None:
                    print()
                print(rendered)
                last_rendered = rendered

        if args.expected_count and snapshot["completed_runs"] >= args.expected_count:
            break
        if args.duration > 0 and (time.time() - started) >= args.duration:
            break
        time.sleep(args.interval)

    if args.live:
        raise SystemExit(0)

    _success(
        "run.watch",
        batch_dir=str(batch_dir),
        checks=len(snapshots),
        latest=snapshots[-1] if snapshots else None,
        snapshots=snapshots,
    )


def cmd_run_cleanup(args: argparse.Namespace) -> None:
    batch_id, batch_dir = _resolve_batch_dir(args.batch_id, args.batch_dir, command="run.cleanup")

    existed = batch_dir.exists()
    if existed:
        shutil.rmtree(batch_dir)

    entries = _read_run_index()
    kept_entries = [item for item in entries if item.get("batch_id") != batch_id and item.get("batch_dir") != str(batch_dir)]
    if len(kept_entries) != len(entries):
        index_path = _run_index_path()
        with index_path.open("w", encoding="utf-8") as fh:
            for item in kept_entries:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    _success(
        "run.cleanup",
        batch_id=batch_id,
        batch_dir=str(batch_dir),
        deleted=existed,
        removed_index_entries=len(entries) - len(kept_entries),
    )


def cmd_run_retry(args: argparse.Namespace) -> None:
    source_batch_id, source_batch_dir = _resolve_batch_dir(args.batch_id, args.batch_dir, command="run.retry")
    source_batch_summary_path = source_batch_dir / "batch-summary.json"
    source_batch_summary = _load_summary_file(source_batch_summary_path)
    if not source_batch_summary:
        _failure(
            "run.retry",
            "batch_not_found",
            "Failed to load source batch summary.",
            batch_dir=str(source_batch_dir),
        )

    source_summaries = _collect_batch_summaries(source_batch_dir)
    if not source_summaries:
        _failure(
            "run.retry",
            "no_runs_found",
            "No run summaries were found in the source batch.",
            batch_dir=str(source_batch_dir),
        )

    selected_runs = [item for item in source_summaries if args.all or not item.get("ok")]
    if not selected_runs:
        _success(
            "run.retry",
            source_batch_id=source_batch_id,
            source_batch_dir=str(source_batch_dir),
            retried_count=0,
            message="No matching runs needed retry.",
        )

    retry_batch_id = args.retry_batch_id or f"{source_batch_id}-retry-{_case_now()}"
    retry_batch_dir = _runs_root() / retry_batch_id
    retry_batch_dir.mkdir(parents=True, exist_ok=True)
    batch_event_log = retry_batch_dir / "events.jsonl"
    _append_event(
        batch_event_log,
        "batch_retry_started",
        source_batch_id=source_batch_id,
        retry_batch_id=retry_batch_id,
        file=source_batch_summary.get("file"),
        count=len(selected_runs),
        concurrency=args.concurrency,
    )

    jobs = []
    for index, source_summary in enumerate(selected_runs):
        jobs.append(
            {
                "run_id": f"{retry_batch_id}-run-{index + 1:03d}",
                "artifacts_dir": retry_batch_dir / f"run-{index + 1:03d}",
                "source_run_id": source_summary.get("run_id"),
            }
        )

    summaries: list[dict[str, Any]] = []

    def worker(job: dict[str, Any]) -> dict[str, Any]:
        _append_event(
            batch_event_log,
            "retry_run_submitted",
            source_batch_id=source_batch_id,
            retry_batch_id=retry_batch_id,
            source_run_id=job["source_run_id"],
            run_id=job["run_id"],
            artifacts_dir=str(job["artifacts_dir"]),
        )
        payload = _run_case_subprocess(
            file=str(source_batch_summary.get("file")),
            run_id=job["run_id"],
            artifacts_dir=job["artifacts_dir"],
            stop_on_error=args.stop_on_error,
            close_created_session=args.close_created_session,
        )
        payload.setdefault("run_id", job["run_id"])
        payload["_source_run_id"] = job["source_run_id"]
        return payload

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        future_map = {executor.submit(worker, job): job for job in jobs}
        for future in as_completed(future_map):
            job = future_map[future]
            try:
                payload = future.result()
            except Exception as exc:
                payload = {
                    "ok": False,
                    "command": "case.run",
                    "run_id": job["run_id"],
                    "artifacts_dir": str(job["artifacts_dir"]),
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                    "_source_run_id": job["source_run_id"],
                }
            payload.setdefault("run_id", job["run_id"])
            payload.setdefault("artifacts_dir", str(job["artifacts_dir"]))
            summaries.append(payload)
            _append_event(
                batch_event_log,
                "retry_run_completed",
                source_batch_id=source_batch_id,
                retry_batch_id=retry_batch_id,
                source_run_id=payload.get("_source_run_id"),
                run_id=payload.get("run_id"),
                ok=payload.get("ok"),
                artifacts_dir=payload.get("artifacts_dir"),
                session_id=(payload.get("session") or {}).get("session_id"),
            )

    summaries.sort(key=lambda item: item.get("run_id", ""))
    retry_batch_summary = _make_batch_summary(retry_batch_id, retry_batch_dir, str(source_batch_summary.get("file")), summaries)
    retry_batch_summary["source_batch_id"] = source_batch_id
    retry_batch_summary["retried_runs"] = [
        {
            "source_run_id": item.get("_source_run_id"),
            "retry_run_id": item.get("run_id"),
            "ok": item.get("ok"),
            "artifacts_dir": item.get("artifacts_dir"),
        }
        for item in summaries
    ]
    _write_batch_summary(retry_batch_dir, retry_batch_summary)
    _append_run_index(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "batch_id": retry_batch_id,
            "file": retry_batch_summary["file"],
            "batch_dir": str(retry_batch_dir),
            "count": retry_batch_summary["count"],
            "ok_count": retry_batch_summary["ok_count"],
            "failed_count": retry_batch_summary["failed_count"],
            "source_batch_id": source_batch_id,
        }
    )
    _append_event(
        batch_event_log,
        "batch_retry_finished",
        source_batch_id=source_batch_id,
        retry_batch_id=retry_batch_id,
        ok=retry_batch_summary["ok"],
        count=retry_batch_summary["count"],
        ok_count=retry_batch_summary["ok_count"],
        failed_count=retry_batch_summary["failed_count"],
    )
    _json_dump(retry_batch_summary, exit_code=0 if retry_batch_summary["ok"] else 1)


def _add_session_target_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--connect-url", help="Connect to the browser through an explicit CDP websocket URL")
    parser.add_argument("--session-id", help="Resolve connect_url from an existing Lexmount session")
    parser.add_argument("--direct-url", action="store_true", help="Use the shared direct websocket URL derived from env")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lexmount browser helper for Codex skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    session = subparsers.add_parser("session", help="Manage browser sessions")
    session_subparsers = session.add_subparsers(dest="session_command", required=True)

    session_create = session_subparsers.add_parser("create", help="Create or reuse a context, then create a session")
    session_create.add_argument("--context-id", help="Reuse an existing context")
    session_create.add_argument("--create-context", action="store_true", help="Create a new context before creating the session")
    session_create.add_argument("--context-mode", default="read_write", type=_normalize_context_mode)
    session_create.add_argument("--browser-mode", default="normal", type=_normalize_browser_mode)
    session_create.add_argument("--metadata-json", dest="metadata", type=_parse_metadata_json, help="JSON object used when --create-context creates a context")
    session_create.set_defaults(func=cmd_session_create)

    session_list = session_subparsers.add_parser("list", help="List sessions for the current project")
    session_list.add_argument("--status", help="Optional status filter, for example active or closed")
    session_list.set_defaults(func=cmd_session_list)

    session_get = session_subparsers.add_parser("get", help="Get one session from the current project")
    session_get.add_argument("--session-id", required=True)
    session_get.set_defaults(func=cmd_session_get)

    session_close = session_subparsers.add_parser("close", help="Close a browser session")
    session_close.add_argument("--session-id", required=True)
    session_close.set_defaults(func=cmd_session_close)

    session_keepalive = session_subparsers.add_parser("keepalive", help="Poll a session to keep observing its status")
    session_keepalive.add_argument("--session-id", required=True)
    session_keepalive.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    session_keepalive.add_argument("--duration", type=float, default=60.0, help="Total watch duration in seconds, use 0 for unbounded")
    session_keepalive.add_argument("--stop-on-inactive", action="store_true", help="Stop when the session is no longer active")
    session_keepalive.set_defaults(func=cmd_session_keepalive)

    context = subparsers.add_parser("context", help="Manage browser contexts")
    context_subparsers = context.add_subparsers(dest="context_command", required=True)

    context_create = context_subparsers.add_parser("create", help="Create a persistent context")
    context_create.add_argument("--metadata-json", dest="metadata", type=_parse_metadata_json, help="JSON object sent as context metadata")
    context_create.set_defaults(func=cmd_context_create)

    context_list = context_subparsers.add_parser("list", help="List contexts for the current project")
    context_list.add_argument("--status", help="Optional status filter, for example available or locked")
    context_list.add_argument("--limit", type=int, default=20)
    context_list.set_defaults(func=cmd_context_list)

    context_get = context_subparsers.add_parser("get", help="Get one context")
    context_get.add_argument("--context-id", required=True)
    context_get.set_defaults(func=cmd_context_get)

    context_delete = context_subparsers.add_parser("delete", help="Delete one context")
    context_delete.add_argument("--context-id", required=True)
    context_delete.set_defaults(func=cmd_context_delete)

    action = subparsers.add_parser("action", help="Run basic browser actions through Playwright")
    action_subparsers = action.add_subparsers(dest="action_command", required=True)

    action_open_url = action_subparsers.add_parser("open-url", help="Open a URL in the target browser")
    _add_session_target_args(action_open_url)
    action_open_url.add_argument("--url", required=True)
    action_open_url.add_argument("--wait-until", default="load", choices=["commit", "domcontentloaded", "load", "networkidle"])
    action_open_url.add_argument("--timeout-ms", type=float, default=30000)
    action_open_url.set_defaults(func=cmd_action_open_url)

    action_wait_selector = action_subparsers.add_parser("wait-selector", help="Wait for a selector to reach a state")
    _add_session_target_args(action_wait_selector)
    action_wait_selector.add_argument("--selector", required=True)
    action_wait_selector.add_argument("--state", default="visible", choices=["attached", "detached", "hidden", "visible"])
    action_wait_selector.add_argument("--timeout-ms", type=float, default=30000)
    action_wait_selector.set_defaults(func=cmd_action_wait_selector)

    action_click = action_subparsers.add_parser("click", help="Click a selector")
    _add_session_target_args(action_click)
    action_click.add_argument("--selector", required=True)
    action_click.add_argument("--timeout-ms", type=float, default=30000)
    action_click.add_argument("--wait-after-ms", type=float, default=0)
    action_click.set_defaults(func=cmd_action_click)

    action_type = action_subparsers.add_parser("type", help="Fill a selector with text")
    _add_session_target_args(action_type)
    action_type.add_argument("--selector", required=True)
    action_type.add_argument("--text", required=True)
    action_type.add_argument("--timeout-ms", type=float, default=30000)
    action_type.add_argument("--press-enter", action="store_true")
    action_type.set_defaults(func=cmd_action_type)

    action_screenshot = action_subparsers.add_parser("screenshot", help="Capture a screenshot")
    _add_session_target_args(action_screenshot)
    action_screenshot.add_argument("--output", help="Output path for the PNG file")
    action_screenshot.add_argument("--full-page", action="store_true")
    action_screenshot.add_argument("--timeout-ms", type=float, default=30000)
    action_screenshot.set_defaults(func=cmd_action_screenshot)

    action_eval = action_subparsers.add_parser("eval", help="Run a JavaScript expression in the current page")
    _add_session_target_args(action_eval)
    action_eval.add_argument("--expression", required=True)
    action_eval.set_defaults(func=cmd_action_eval)

    action_snapshot = action_subparsers.add_parser("snapshot", help="Capture page title, URL, HTML, and body text")
    _add_session_target_args(action_snapshot)
    action_snapshot.add_argument("--timeout-ms", type=float, default=30000)
    action_snapshot.add_argument("--max-chars", type=int, default=8000)
    action_snapshot.set_defaults(func=cmd_action_snapshot)

    case = subparsers.add_parser("case", help="Validate or run a multi-step browser case file")
    case_subparsers = case.add_subparsers(dest="case_command", required=True)

    case_validate = case_subparsers.add_parser("validate", help="Validate a case file")
    case_validate.add_argument("--file", required=True, help="Path to a JSON or YAML case file")
    case_validate.set_defaults(func=cmd_case_validate)

    case_run = case_subparsers.add_parser("run", help="Run a case file")
    case_run.add_argument("--file", required=True, help="Path to a JSON or YAML case file")
    case_run.add_argument("--run-id", help="Optional explicit run id used in output summaries")
    case_run.add_argument("--artifacts-dir", help="Directory for run artifacts, defaults to /tmp/lexmount-runs/<run_id>")
    case_run.add_argument("--stop-on-error", action="store_true", help="Stop execution when a step fails")
    case_run.add_argument("--close-created-session", action="store_true", help="Close a session created by session.create inside the case file")
    case_run.set_defaults(func=cmd_case_run)

    run = subparsers.add_parser("run", help="Submit and inspect local batches of case runs")
    run_subparsers = run.add_subparsers(dest="run_command", required=True)

    run_submit = run_subparsers.add_parser("submit", help="Run the same case file multiple times and collect summaries")
    run_submit.add_argument("--file", required=True, help="Path to a JSON or YAML case file")
    run_submit.add_argument("--count", type=int, default=1, help="Number of runs to execute")
    run_submit.add_argument("--concurrency", type=int, default=1, help="Number of case subprocesses to run in parallel")
    run_submit.add_argument("--batch-id", help="Optional explicit batch id")
    run_submit.add_argument("--stop-on-error", action="store_true", help="Pass stop-on-error through to each case run")
    run_submit.add_argument("--close-created-session", action="store_true", help="Close any session created inside each case run")
    run_submit.set_defaults(func=cmd_run_submit)

    run_list = run_subparsers.add_parser("list", help="List locally recorded run batches")
    run_list.add_argument("--limit", type=int, default=20, help="Maximum number of batches to return")
    run_list.set_defaults(func=cmd_run_list)

    run_summary = run_subparsers.add_parser("summary", help="Show summary for one batch")
    run_summary.add_argument("--batch-id", help="Batch id under the local runs root")
    run_summary.add_argument("--batch-dir", help="Explicit path to a batch directory")
    run_summary.set_defaults(func=cmd_run_summary)

    run_watch = run_subparsers.add_parser("watch", help="Poll a batch directory and report progress")
    run_watch.add_argument("--batch-id", help="Batch id under the local runs root")
    run_watch.add_argument("--batch-dir", help="Explicit path to a batch directory")
    run_watch.add_argument("--expected-count", type=int, default=0, help="Stop once this many runs are present")
    run_watch.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    run_watch.add_argument("--duration", type=float, default=30.0, help="Maximum watch duration in seconds, use 0 for unbounded")
    run_watch.add_argument("--live", action="store_true", help="Print compact human-readable snapshots instead of JSON")
    run_watch.add_argument("--changes-only", action="store_true", help="With --live, only print when the rendered snapshot changes")
    run_watch.set_defaults(func=cmd_run_watch)

    run_retry = run_subparsers.add_parser("retry", help="Retry failed runs from an existing batch into a new batch")
    run_retry.add_argument("--batch-id", help="Source batch id under the local runs root")
    run_retry.add_argument("--batch-dir", help="Explicit path to a source batch directory")
    run_retry.add_argument("--retry-batch-id", help="Optional explicit batch id for the retry batch")
    run_retry.add_argument("--all", action="store_true", help="Retry all runs instead of only failed runs")
    run_retry.add_argument("--concurrency", type=int, default=1, help="Number of case subprocesses to run in parallel")
    run_retry.add_argument("--stop-on-error", action="store_true", help="Pass stop-on-error through to each retry case run")
    run_retry.add_argument("--close-created-session", action="store_true", help="Close any session created inside each retry case run")
    run_retry.set_defaults(func=cmd_run_retry)

    run_cleanup = run_subparsers.add_parser("cleanup", help="Delete one local batch directory and remove its index entry")
    run_cleanup.add_argument("--batch-id", help="Batch id under the local runs root")
    run_cleanup.add_argument("--batch-dir", help="Explicit path to a batch directory")
    run_cleanup.set_defaults(func=cmd_run_cleanup)

    research = subparsers.add_parser("research", help="Run built-in streaming research templates")
    research_subparsers = research.add_subparsers(dest="research_command", required=True)

    research_knowledge = research_subparsers.add_parser(
        "knowledge",
        help="One producer browser searches and streams links to multiple consumer browsers for content capture",
    )
    research_knowledge.add_argument("--query", required=True, help="Search query used by the producer browser")
    research_knowledge.add_argument("--max-links", type=int, default=100, help="Maximum number of result links to enqueue")
    research_knowledge.add_argument(
        "--min-success-pages",
        type=int,
        default=0,
        help="Keep producing beyond --max-links until at least this many pages have been captured successfully, or search pages are exhausted",
    )
    research_knowledge.add_argument("--consumer-count", type=int, default=4, help="Number of consumer browsers to run in parallel")
    research_knowledge.add_argument("--queue-size", type=int, default=20, help="Maximum buffered links between producer and consumers")
    research_knowledge.add_argument("--search-engine", default="bing", choices=["bing", "google", "duckduckgo"])
    research_knowledge.add_argument(
        "--search-url-template",
        help="Optional URL template with {query}, {offset}, and {page}; overrides the selected engine default",
    )
    research_knowledge.add_argument(
        "--result-selector",
        help="Optional CSS selector for result links; overrides the selected engine default",
    )
    research_knowledge.add_argument("--page-size", type=int, default=10, help="Offset increment between search result pages")
    research_knowledge.add_argument("--search-pages-max", type=int, default=20, help="Maximum number of search result pages to scan")
    research_knowledge.add_argument("--producer-browser-mode", default="normal", type=_normalize_browser_mode)
    research_knowledge.add_argument("--consumer-browser-mode", default="normal", type=_normalize_browser_mode)
    research_knowledge.add_argument(
        "--search-wait-until",
        default="domcontentloaded",
        choices=["commit", "domcontentloaded", "load", "networkidle"],
    )
    research_knowledge.add_argument(
        "--page-wait-until",
        default="domcontentloaded",
        choices=["commit", "domcontentloaded", "load", "networkidle"],
    )
    research_knowledge.add_argument("--search-timeout-ms", type=float, default=30000)
    research_knowledge.add_argument("--page-timeout-ms", type=float, default=30000)
    research_knowledge.add_argument("--content-selector", default="body", help="Selector consumers wait for before snapshotting")
    research_knowledge.add_argument(
        "--content-wait-state",
        default="visible",
        choices=["attached", "detached", "hidden", "visible"],
    )
    research_knowledge.add_argument("--max-chars", type=int, default=8000, help="Maximum HTML/text chars to persist per page")
    research_knowledge.add_argument("--run-id", help="Optional explicit research run id")
    research_knowledge.add_argument("--output-dir", help="Directory for links, page artifacts, logs, and summary output")
    research_knowledge.add_argument("--screenshot", action="store_true", help="Capture a full-page screenshot for each consumed page")
    research_knowledge.add_argument("--keep-sessions", action="store_true", help="Keep producer and consumer sessions open after the run")
    research_knowledge.set_defaults(func=cmd_research_knowledge)

    prepare = subparsers.add_parser("prepare", help="Backward-compatible alias for session create")
    prepare.add_argument("--context-id", help="Reuse an existing context")
    prepare.add_argument("--create-context", action="store_true", help="Create a new context before creating the session")
    prepare.add_argument("--context-mode", default="read_write", type=_normalize_context_mode)
    prepare.add_argument("--browser-mode", default="normal", type=_normalize_browser_mode)
    prepare.add_argument("--metadata-json", dest="metadata", type=_parse_metadata_json, help="JSON object used when --create-context creates a context")
    prepare.set_defaults(func=cmd_prepare)

    list_contexts = subparsers.add_parser("list-contexts", help="Backward-compatible alias for context list")
    list_contexts.add_argument("--status", help="Optional status filter")
    list_contexts.add_argument("--limit", type=int, default=20)
    list_contexts.set_defaults(func=cmd_list_contexts)

    close_session = subparsers.add_parser("close-session", help="Backward-compatible alias for session close")
    close_session.add_argument("--session-id", required=True)
    close_session.set_defaults(func=cmd_close_session)

    direct_url = subparsers.add_parser("direct-url", help="Build the shared direct websocket URL")
    direct_url.set_defaults(func=cmd_direct_url)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
