"""Playwright-backed browser actions used by the runtime CLI skill surface."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lex_browser_runtime.browser.lexmount import (
    LexmountBrowserAdmin,
    build_direct_connect_url,
)
from lex_browser_runtime.browser.models import BrowserConfigError, BrowserRuntimeError

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]
SelectorState = Literal["attached", "detached", "hidden", "visible"]
BrowserActionName = Literal[
    "open-url",
    "wait-selector",
    "click",
    "type",
    "screenshot",
    "eval",
    "snapshot",
]


class BrowserActionTarget(BaseModel):
    """Target browser for a runtime action."""

    model_config = ConfigDict(extra="forbid")

    connect_url: str | None = None
    session_id: str | None = None
    direct_url: bool = False


class OpenUrlRequest(BaseModel):
    """Request for opening a URL in the target page."""

    url: str
    wait_until: WaitUntil = "load"
    timeout_ms: float = Field(default=30000, gt=0)


class WaitSelectorRequest(BaseModel):
    """Request for waiting on a selector."""

    selector: str
    state: SelectorState = "visible"
    timeout_ms: float = Field(default=30000, gt=0)


class ClickRequest(BaseModel):
    """Request for clicking a selector."""

    selector: str
    timeout_ms: float = Field(default=30000, gt=0)
    wait_after_ms: float = Field(default=0, ge=0)


class TypeRequest(BaseModel):
    """Request for filling a selector with text."""

    selector: str
    text: str
    timeout_ms: float = Field(default=30000, gt=0)
    press_enter: bool = False


class ScreenshotRequest(BaseModel):
    """Request for capturing a screenshot."""

    output: str | None = None
    full_page: bool = False
    timeout_ms: float = Field(default=30000, gt=0)


class EvalRequest(BaseModel):
    """Request for evaluating a JavaScript expression."""

    expression: str


class SnapshotRequest(BaseModel):
    """Request for capturing page HTML and body text."""

    timeout_ms: float = Field(default=30000, gt=0)
    max_chars: int = 8000


BrowserActionRequest = (
    OpenUrlRequest
    | WaitSelectorRequest
    | ClickRequest
    | TypeRequest
    | ScreenshotRequest
    | EvalRequest
    | SnapshotRequest
)


class BrowserActionResult(BaseModel):
    """Structured result returned after running a browser action."""

    action: BrowserActionName
    result: dict[str, Any]


def resolve_browser_action_connect_url(
    target: BrowserActionTarget,
    *,
    admin: LexmountBrowserAdmin | None = None,
) -> str:
    """Resolve a CDP connect URL from explicit URL, session id, or direct mode."""

    if target.connect_url:
        return target.connect_url
    if target.direct_url:
        return build_direct_connect_url()
    if target.session_id:
        resolved_admin = admin or LexmountBrowserAdmin()
        session = resolved_admin.get_session(target.session_id)
        if session.connect_url:
            return session.connect_url
        raise BrowserRuntimeError(
            f"Session '{target.session_id}' does not expose a connect URL."
        )
    raise BrowserRuntimeError(
        "Pass one of connect_url, session_id, or direct_url for browser action target."
    )


def get_or_create_page(context: Any) -> Any:
    """Return the newest page in a Playwright context, creating one if needed."""

    pages = getattr(context, "pages", None)
    if pages:
        return pages[-1]
    return context.new_page()


def execute_browser_action_on_page(
    page: Any,
    action: BrowserActionName,
    request: BrowserActionRequest,
) -> BrowserActionResult:
    """Execute one runtime browser action against an existing Playwright page."""

    if action == "open-url":
        if not isinstance(request, OpenUrlRequest):
            raise TypeError("open-url action requires OpenUrlRequest")
        response = page.goto(
            request.url,
            wait_until=request.wait_until,
            timeout=request.timeout_ms,
        )
        return BrowserActionResult(
            action=action,
            result={
                "url": page.url,
                "title": page.title(),
                "status": response.status if response else None,
            },
        )

    if action == "wait-selector":
        if not isinstance(request, WaitSelectorRequest):
            raise TypeError("wait-selector action requires WaitSelectorRequest")
        locator = page.wait_for_selector(
            request.selector,
            state=request.state,
            timeout=request.timeout_ms,
        )
        return BrowserActionResult(
            action=action,
            result={
                "url": page.url,
                "selector": request.selector,
                "state": request.state,
                "text": locator.text_content() if locator else None,
            },
        )

    if action == "click":
        if not isinstance(request, ClickRequest):
            raise TypeError("click action requires ClickRequest")
        page.click(request.selector, timeout=request.timeout_ms)
        if request.wait_after_ms:
            page.wait_for_timeout(request.wait_after_ms)
        return BrowserActionResult(
            action=action,
            result={"url": page.url, "selector": request.selector, "clicked": True},
        )

    if action == "type":
        if not isinstance(request, TypeRequest):
            raise TypeError("type action requires TypeRequest")
        page.fill(request.selector, request.text, timeout=request.timeout_ms)
        if request.press_enter:
            page.press(request.selector, "Enter", timeout=request.timeout_ms)
        return BrowserActionResult(
            action=action,
            result={
                "url": page.url,
                "selector": request.selector,
                "typed": True,
                "press_enter": request.press_enter,
            },
        )

    if action == "screenshot":
        if not isinstance(request, ScreenshotRequest):
            raise TypeError("screenshot action requires ScreenshotRequest")
        output_path = request.output or str(
            Path("/tmp") / f"lexmount-screenshot-{int(time.time())}.png"
        )
        page.screenshot(
            path=output_path,
            full_page=request.full_page,
            timeout=request.timeout_ms,
        )
        return BrowserActionResult(
            action=action,
            result={
                "url": page.url,
                "path": output_path,
                "full_page": request.full_page,
            },
        )

    if action == "eval":
        if not isinstance(request, EvalRequest):
            raise TypeError("eval action requires EvalRequest")
        value = page.evaluate(request.expression)
        return BrowserActionResult(
            action=action,
            result={
                "url": page.url,
                "expression": request.expression,
                "value": value,
            },
        )

    if action == "snapshot":
        if not isinstance(request, SnapshotRequest):
            raise TypeError("snapshot action requires SnapshotRequest")
        html = page.content()
        body_text = page.locator("body").inner_text(timeout=request.timeout_ms)
        if request.max_chars > 0:
            html = html[: request.max_chars]
            body_text = body_text[: request.max_chars]
        return BrowserActionResult(
            action=action,
            result={
                "url": page.url,
                "title": page.title(),
                "html": html,
                "text": body_text,
            },
        )

    raise ValueError(f"Unsupported browser action: {action}")


def run_browser_action(
    *,
    connect_url: str,
    action: BrowserActionName,
    request: BrowserActionRequest,
) -> BrowserActionResult:
    """Connect to a browser over CDP and execute one action."""

    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception as exc:
        raise BrowserConfigError(
            "Failed to import Playwright. Install lex-browser-runtime[browser] "
            "or provide an environment that already includes playwright."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(connect_url)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = get_or_create_page(context)
            return execute_browser_action_on_page(page, action, request)
        finally:
            browser.close()
