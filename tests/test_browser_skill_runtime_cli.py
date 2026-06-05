from __future__ import annotations

import builtins
import json
import sys
from types import ModuleType
from types import SimpleNamespace
from typing import Any

import pytest

from lex_browser_runtime.browser.actions import (
    BrowserActionTarget,
    ClickRequest,
    EvalRequest,
    SnapshotRequest,
    execute_browser_action_on_page,
    resolve_browser_action_connect_url,
    run_browser_action,
)
from lex_browser_runtime.browser.cases import (
    run_case_file,
    run_case_step,
    validate_case_file,
    validate_case_spec,
)
from lex_browser_runtime.browser.lexmount import (
    LexmountBrowserAdmin,
    build_direct_connect_url,
    normalize_lexmount_sdk_error,
)
from lex_browser_runtime.browser.models import BrowserRuntimeError
from lex_browser_runtime.browser.models import BrowserConfigError
from lex_browser_runtime.cli import main as cli_main


class _FakeSession:
    id = "session_123"
    session_id = "session_123"
    status = "active"
    browser_type = "chromium"
    project_id = "project_123"
    created_at = "2026-05-20T00:00:00Z"
    inspect_url = "https://browser.lexmount.test/inspect"
    inspect_url_dbg = None
    container_id = "container_123"
    connect_url = "wss://cdp.lexmount.test/devtools/browser/session_123"
    ws = None


class _FakeContext:
    id = "context_123"
    status = "available"
    created_at = "2026-05-20T00:00:00Z"
    updated_at = "2026-05-20T00:00:01Z"
    metadata = {"owner": "test"}


class _FakeSessions:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    def create(self, **kwargs: Any) -> _FakeSession:
        self.created.append(kwargs)
        return _FakeSession()

    def list(self, status: str | None = None) -> Any:
        return SimpleNamespace(
            sessions=[_FakeSession()],
            pagination=SimpleNamespace(
                current_page=1,
                page_size=20,
                total_count=1,
                total_pages=1,
                active_count=1,
                closed_count=0,
            ),
            status=status,
        )

    def delete(self, *, session_id: str) -> None:
        self.deleted.append(session_id)


class _FakeContexts:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    def create(self, metadata: dict[str, Any] | None = None) -> _FakeContext:
        self.created.append({"metadata": metadata})
        return _FakeContext()

    def list(self, status: str | None = None, limit: int | None = None) -> list[Any]:
        del status, limit
        return [_FakeContext()]

    def get(self, context_id: str) -> _FakeContext:
        assert context_id == "context_123"
        return _FakeContext()

    def delete(self, context_id: str) -> None:
        self.deleted.append(context_id)


class _FakeClient:
    base_url = "https://api.lexmount.test"
    project_id = "project_123"

    def __init__(self) -> None:
        self.sessions = _FakeSessions()
        self.contexts = _FakeContexts()


def _session_record(session_id: str) -> Any:
    return SimpleNamespace(
        id=session_id,
        session_id=session_id,
        status="active",
        browser_type="chromium",
        project_id="project_123",
        created_at="2026-05-20T00:00:00Z",
        inspect_url=None,
        inspect_url_dbg=None,
        container_id=None,
        connect_url=f"wss://cdp.lexmount.test/{session_id}",
        ws=None,
    )


def test_direct_connect_url_uses_region_base_and_escapes_credentials() -> None:
    url = build_direct_connect_url(
        api_key="key with space",
        project_id="project/one",
        base_url="https://api.lexmount.com",
    )

    assert url == (
        "wss://api.lexmount.com/connection?"
        "project_id=project%2Fone&api_key=key+with+space"
    )


def test_parallel_limit_error_is_normalized_with_structured_code() -> None:
    class FakeAPIError(Exception):
        status_code = 429
        response = {"detail": "active session limit reached"}

    error = normalize_lexmount_sdk_error(FakeAPIError("parallel browser quota"))

    assert error.code == "browser_parallel_limit_reached"
    assert "浏览器并行额度已达上限" in error.message
    assert error.status_code == 429
    assert error.response == {"detail": "active session limit reached"}


def test_admin_session_create_matches_browser_skill_context_flow() -> None:
    client = _FakeClient()
    admin = LexmountBrowserAdmin(client)

    result = admin.create_session(
        create_context=True,
        context_mode="read_write",
        browser_mode="normal",
        metadata={"owner": "test"},
    )

    assert client.contexts.created == [{"metadata": {"owner": "test"}}]
    assert client.sessions.created == [
        {
            "browser_mode": "normal",
            "context": {"id": "context_123", "mode": "read_write"},
        }
    ]
    assert result.context_id == "context_123"
    assert result.created_context is True
    assert result.session.session_id == "session_123"
    assert (
        result.session.connect_url
        == "wss://cdp.lexmount.test/devtools/browser/session_123"
    )


def test_admin_session_create_cleans_new_context_on_session_failure() -> None:
    class FailingSessions(_FakeSessions):
        def create(self, **kwargs: Any) -> _FakeSession:
            self.created.append(kwargs)
            raise RuntimeError("session create failed")

    client = _FakeClient()
    client.sessions = FailingSessions()
    admin = LexmountBrowserAdmin(client)

    with pytest.raises(BrowserRuntimeError, match="session create failed"):
        admin.create_session(create_context=True, metadata={"owner": "test"})

    assert client.contexts.created == [{"metadata": {"owner": "test"}}]
    assert client.contexts.deleted == ["context_123"]


def test_admin_get_session_searches_paginated_results() -> None:
    class PagedSessions:
        def list(
            self,
            *,
            status: str | None = None,
            page: int | None = None,
            limit: int | None = None,
            page_size: int | None = None,
        ) -> Any:
            del status, limit, page_size
            current_page = page or 1
            sessions = (
                [_session_record("session_page_1")]
                if current_page == 1
                else [_session_record("session_page_2")]
            )
            return SimpleNamespace(
                sessions=sessions,
                pagination=SimpleNamespace(
                    current_page=current_page,
                    page_size=1,
                    total_count=2,
                    total_pages=2,
                    active_count=2,
                    closed_count=0,
                ),
            )

    client: Any = _FakeClient()
    client.sessions = PagedSessions()
    admin = LexmountBrowserAdmin(client)

    session = admin.get_session("session_page_2")

    assert session.session_id == "session_page_2"
    assert session.connect_url == "wss://cdp.lexmount.test/session_page_2"


def test_admin_keepalive_duration_zero_runs_single_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(
        "lex_browser_runtime.browser.lexmount.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )
    admin = LexmountBrowserAdmin(_FakeClient())

    result = admin.keepalive_session(
        session_id="session_123",
        duration=0,
        interval=0.01,
        stop_on_inactive=False,
    )

    assert result["checks"] == 1
    assert result["final_status"] == "active"
    assert result["snapshots"][0]["session"]["session_id"] == "session_123"
    assert sleeps == []


def test_resolve_action_target_prefers_explicit_connect_url() -> None:
    target = BrowserActionTarget(connect_url="ws://explicit")

    assert (
        resolve_browser_action_connect_url(
            target, admin=LexmountBrowserAdmin(_FakeClient())
        )
        == "ws://explicit"
    )


def test_resolve_action_target_can_use_session_id() -> None:
    target = BrowserActionTarget(session_id="session_123")

    assert (
        resolve_browser_action_connect_url(
            target, admin=LexmountBrowserAdmin(_FakeClient())
        )
        == "wss://cdp.lexmount.test/devtools/browser/session_123"
    )


class _FakeLocator:
    def text_content(self) -> str:
        return "ready"

    def inner_text(self, *, timeout: float) -> str:
        assert timeout == 30000
        return "body text"


class _FakePage:
    url = "https://example.com"

    def __init__(self) -> None:
        self.clicked: list[tuple[str, float]] = []

    def click(self, selector: str, *, timeout: float) -> None:
        self.clicked.append((selector, timeout))

    def wait_for_timeout(self, timeout: float) -> None:
        self.clicked.append(("wait", timeout))

    def content(self) -> str:
        return "<html><body>body text</body></html>"

    def locator(self, selector: str) -> _FakeLocator:
        assert selector == "body"
        return _FakeLocator()

    def title(self) -> str:
        return "Example"

    def goto(self, url: str, *, wait_until: str, timeout: float) -> Any:
        assert wait_until == "load"
        assert timeout == 30000
        self.url = url
        return type("Response", (), {"status": 200})()

    def wait_for_selector(
        self, selector: str, *, state: str, timeout: float
    ) -> _FakeLocator:
        assert selector == "body"
        assert state == "visible"
        assert timeout == 30000
        return _FakeLocator()

    def fill(self, selector: str, text: str, *, timeout: float) -> None:
        self.clicked.append((f"fill:{selector}:{text}", timeout))

    def press(self, selector: str, key: str, *, timeout: float) -> None:
        self.clicked.append((f"press:{selector}:{key}", timeout))

    def screenshot(self, *, path: str, full_page: bool, timeout: float) -> None:
        self.clicked.append((f"screenshot:{path}:{full_page}", timeout))

    def evaluate(self, expression: str) -> str:
        return f"eval:{expression}"


def test_execute_click_and_snapshot_actions_on_page() -> None:
    page = _FakePage()

    click_result = execute_browser_action_on_page(
        page,
        "click",
        ClickRequest(selector="button", wait_after_ms=250),
    )
    snapshot_result = execute_browser_action_on_page(
        page,
        "snapshot",
        SnapshotRequest(max_chars=9),
    )

    assert page.clicked == [("button", 30000), ("wait", 250)]
    assert click_result.result == {
        "url": "https://example.com",
        "selector": "button",
        "clicked": True,
    }
    assert snapshot_result.result["title"] == "Example"
    assert snapshot_result.result["html"] == "<html><bo"
    assert snapshot_result.result["text"] == "body text"


def test_readonly_browser_action_falls_back_to_raw_cdp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingChromium:
        def connect_over_cdp(self, connect_url: str) -> Any:
            assert connect_url == "ws://browser"
            raise RuntimeError("targetInfo shared_worker assertion")

    class FakePlaywright:
        chromium = FailingChromium()

    class FakeSyncPlaywright:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, *args: Any) -> None:
            return None

    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        def recv(self) -> str:
            message = self.sent[-1]
            method = message["method"]
            if method == "Target.getTargets":
                result = {
                    "targetInfos": [
                        {
                            "targetId": "worker",
                            "type": "shared_worker",
                            "url": "blob:https://example.com/worker",
                        },
                        {
                            "targetId": "page",
                            "type": "page",
                            "url": "https://example.com",
                        },
                    ]
                }
            elif method == "Target.attachToTarget":
                result = {"sessionId": "session-page"}
            elif method == "Runtime.evaluate":
                result = {
                    "result": {
                        "value": {
                            "url": "https://example.com",
                            "title": "Example",
                            "html": "<html><body>hello</body></html>",
                            "text": "hello",
                        }
                    }
                }
            else:
                result = {}
            return json.dumps({"id": message["id"], "result": result})

        def close(self) -> None:
            return None

    fake_socket = FakeWebSocket()
    sync_api_module = ModuleType("playwright.sync_api")
    setattr(sync_api_module, "sync_playwright", FakeSyncPlaywright)
    websocket_module = ModuleType("websocket")
    setattr(websocket_module, "create_connection", lambda url, timeout: fake_socket)
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_module)
    monkeypatch.setitem(sys.modules, "websocket", websocket_module)

    result = run_browser_action(
        connect_url="ws://browser",
        action="snapshot",
        request=SnapshotRequest(max_chars=12),
    )

    assert result.result["fallback"] == "cdp"
    assert result.result["url"] == "https://example.com"
    assert result.result["html"] == "<html><body>"
    assert any(
        message["method"] == "Target.attachToTarget" for message in fake_socket.sent
    )


def test_eval_browser_action_fallback_wraps_arrow_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingChromium:
        def connect_over_cdp(self, connect_url: str) -> Any:
            del connect_url
            raise RuntimeError("targetInfo shared_worker assertion")

    class FakePlaywright:
        chromium = FailingChromium()

    class FakeSyncPlaywright:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, *args: Any) -> None:
            return None

    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        def recv(self) -> str:
            message = self.sent[-1]
            method = message["method"]
            if method == "Target.getTargets":
                result = {
                    "targetInfos": [
                        {
                            "targetId": "page",
                            "type": "page",
                            "url": "https://example.com",
                        }
                    ]
                }
            elif method == "Target.attachToTarget":
                result = {"sessionId": "session-page"}
            elif method == "Runtime.evaluate":
                result = {"result": {"value": 42}}
            else:
                result = {}
            return json.dumps({"id": message["id"], "result": result})

        def close(self) -> None:
            return None

    fake_socket = FakeWebSocket()
    sync_api_module = ModuleType("playwright.sync_api")
    setattr(sync_api_module, "sync_playwright", FakeSyncPlaywright)
    websocket_module = ModuleType("websocket")
    setattr(websocket_module, "create_connection", lambda url, timeout: fake_socket)
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_module)
    monkeypatch.setitem(sys.modules, "websocket", websocket_module)

    result = run_browser_action(
        connect_url="ws://browser",
        action="eval",
        request=EvalRequest(expression="() => 42"),
    )

    runtime_calls = [
        message
        for message in fake_socket.sent
        if message["method"] == "Runtime.evaluate"
    ]
    assert result.result["fallback"] == "cdp"
    assert result.result["value"] == 42
    assert runtime_calls[0]["params"]["expression"] == "(() => 42)()"


def test_readonly_browser_action_falls_back_when_playwright_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        def recv(self) -> str:
            message = self.sent[-1]
            method = message["method"]
            if method == "Target.getTargets":
                result = {
                    "targetInfos": [
                        {
                            "targetId": "page",
                            "type": "page",
                            "url": "https://example.com",
                        }
                    ]
                }
            elif method == "Target.attachToTarget":
                result = {"sessionId": "session-page"}
            elif method == "Runtime.evaluate":
                result = {"result": {"value": 7}}
            else:
                result = {}
            return json.dumps({"id": message["id"], "result": result})

        def close(self) -> None:
            return None

    fake_socket = FakeWebSocket()
    websocket_module = ModuleType("websocket")
    setattr(websocket_module, "create_connection", lambda url, timeout: fake_socket)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    monkeypatch.setitem(sys.modules, "websocket", websocket_module)

    result = run_browser_action(
        connect_url="ws://browser",
        action="eval",
        request=EvalRequest(expression="7"),
    )

    assert result.result["fallback"] == "cdp"
    assert result.result["value"] == 7


def test_eval_browser_action_cdp_fallback_raises_javascript_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeWebSocket:
        def __init__(self) -> None:
            self.sent: list[dict[str, Any]] = []

        def send(self, raw: str) -> None:
            self.sent.append(json.loads(raw))

        def recv(self) -> str:
            message = self.sent[-1]
            method = message["method"]
            if method == "Target.getTargets":
                result = {
                    "targetInfos": [
                        {
                            "targetId": "page",
                            "type": "page",
                            "url": "https://example.com",
                        }
                    ]
                }
            elif method == "Target.attachToTarget":
                result = {"sessionId": "session-page"}
            elif method == "Runtime.evaluate":
                result = {
                    "result": {
                        "type": "object",
                        "subtype": "error",
                        "description": "ReferenceError: missingValue is not defined",
                    },
                    "exceptionDetails": {
                        "text": "Uncaught",
                        "exception": {
                            "description": "ReferenceError: missingValue is not defined"
                        },
                    },
                }
            else:
                result = {}
            return json.dumps({"id": message["id"], "result": result})

        def close(self) -> None:
            return None

    websocket_module = ModuleType("websocket")
    setattr(websocket_module, "create_connection", lambda url, timeout: FakeWebSocket())
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    monkeypatch.setitem(sys.modules, "websocket", websocket_module)

    with pytest.raises(
        BrowserRuntimeError,
        match="JavaScript error: Uncaught: ReferenceError: missingValue",
    ):
        run_browser_action(
            connect_url="ws://browser",
            action="eval",
            request=EvalRequest(expression="() => missingValue"),
        )


def test_case_validate_matches_browser_skill_shape(tmp_path: Any) -> None:
    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "target": {"connect_url": "ws://browser"},
                "steps": [
                    {"action": "open-url", "url": "https://example.com"},
                    {"action": "snapshot", "max_chars": 100},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = validate_case_file(case_path)

    assert result.valid is True
    assert result.step_count == 2
    assert validate_case_spec({"steps": [{"action": "click"}]}) == [
        "steps[0] missing required field 'selector'"
    ]


def test_run_case_step_snapshot_can_write_artifact(tmp_path: Any) -> None:
    page = _FakePage()

    result = run_case_step(
        page,
        {"action": "snapshot", "max_chars": 9, "output": "snapshot.json"},
        tmp_path,
        0,
    )

    assert result["html"] == "<html><bo"
    payload = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert payload["title"] == "Example"
    assert payload["text"] == "body text"


def test_run_case_file_closes_created_session_on_cdp_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    class FakeCreateResult:
        session = SimpleNamespace(connect_url="ws://created-session")
        created_context = False
        context_id = None

        def model_dump(self, *, mode: str) -> dict[str, Any]:
            assert mode == "json"
            return {
                "session": {
                    "session_id": "created_session",
                    "connect_url": "ws://created-session",
                }
            }

    class FakeAdmin:
        def __init__(self) -> None:
            self.closed_sessions: list[str] = []

        def create_session(self, **kwargs: Any) -> FakeCreateResult:
            assert kwargs["browser_mode"] == "normal"
            return FakeCreateResult()

        def close_session(self, session_id: str) -> None:
            self.closed_sessions.append(session_id)

    class FailingChromium:
        def connect_over_cdp(self, connect_url: str) -> Any:
            assert connect_url == "ws://created-session"
            raise RuntimeError("cdp unavailable")

    class FakePlaywright:
        chromium = FailingChromium()

    class FakeSyncPlaywright:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, *args: Any) -> None:
            return None

    admin = FakeAdmin()
    sync_api_module = ModuleType("playwright.sync_api")
    setattr(sync_api_module, "sync_playwright", FakeSyncPlaywright)
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api_module)
    monkeypatch.setattr(
        "lex_browser_runtime.browser.cases.LexmountBrowserAdmin", lambda: admin
    )

    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "session": {"create": True},
                "close_created_session": True,
                "steps": [{"action": "snapshot"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="cdp unavailable"):
        run_case_file(file=case_path, artifacts_dir=tmp_path / "artifacts")

    assert admin.closed_sessions == ["created_session"]
    events = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "events.jsonl").read_text().splitlines()
    ]
    assert any(
        event["type"] == "session_closed"
        and event["session_id"] == "created_session"
        and event["ok"] is True
        for event in events
    )


def test_run_case_file_closes_created_session_on_playwright_import_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    class FakeCreateResult:
        session = SimpleNamespace(connect_url="ws://created-session")
        created_context = False
        context_id = None

        def model_dump(self, *, mode: str) -> dict[str, Any]:
            assert mode == "json"
            return {
                "session": {
                    "session_id": "created_session",
                    "connect_url": "ws://created-session",
                }
            }

    class FakeAdmin:
        def __init__(self) -> None:
            self.closed_sessions: list[str] = []

        def create_session(self, **kwargs: Any) -> FakeCreateResult:
            assert kwargs["browser_mode"] == "normal"
            return FakeCreateResult()

        def close_session(self, session_id: str) -> None:
            self.closed_sessions.append(session_id)

    admin = FakeAdmin()
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        if name == "playwright.sync_api":
            raise ModuleNotFoundError("No module named 'playwright'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        "lex_browser_runtime.browser.cases.LexmountBrowserAdmin", lambda: admin
    )

    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(
            {
                "session": {"create": True},
                "close_created_session": True,
                "steps": [{"action": "snapshot"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BrowserConfigError, match="Failed to import Playwright"):
        run_case_file(file=case_path, artifacts_dir=tmp_path / "artifacts")

    assert admin.closed_sessions == ["created_session"]
    events = [
        json.loads(line)
        for line in (tmp_path / "artifacts" / "events.jsonl").read_text().splitlines()
    ]
    assert any(
        event["type"] == "session_closed"
        and event["session_id"] == "created_session"
        and event["ok"] is True
        for event in events
    )


def test_cli_direct_url_masks_secret_by_default(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LEXMOUNT_API_KEY", "key")
    monkeypatch.setenv("LEXMOUNT_PROJECT_ID", "project")
    monkeypatch.delenv("LEXMOUNT_BASE_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        cli_main(["direct-url"])

    assert exc_info.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "command": "direct-url",
        "mode": "direct",
        "connect_url": "wss://api.lexmount.cn/connection?project_id=project&api_key=***",
        "masked": True,
    }


def test_cli_direct_url_can_reveal_secret_explicitly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LEXMOUNT_API_KEY", "key")
    monkeypatch.setenv("LEXMOUNT_PROJECT_ID", "project")
    monkeypatch.delenv("LEXMOUNT_BASE_URL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        cli_main(["direct-url", "--reveal-url"])

    assert exc_info.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "command": "direct-url",
        "mode": "direct",
        "connect_url": "wss://api.lexmount.cn/connection?project_id=project&api_key=key",
        "masked": False,
    }
