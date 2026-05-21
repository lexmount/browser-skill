from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from lex_browser_runtime import ExistingCdpBackend, LexBrowserRuntime
from lex_browser_runtime.browser import (
    BrowserRuntimeError,
    CreateBrowserRequest,
    LexmountBackend,
)


def test_existing_cdp_backend_returns_stable_session() -> None:
    backend = ExistingCdpBackend(
        "ws://127.0.0.1:9222/devtools/browser/test",
        session_id="session-a",
        inspect_url="http://127.0.0.1:9222",
    )

    session = asyncio.run(backend.create_browser(CreateBrowserRequest()))
    asyncio.run(backend.close_browser(session.id))

    assert session.id == "session-a"
    assert session.backend == "existing-cdp"
    assert session.cdp_url == "ws://127.0.0.1:9222/devtools/browser/test"
    assert session.inspect_url == "http://127.0.0.1:9222"


def test_runtime_records_browser_lifecycle_trace() -> None:
    runtime = LexBrowserRuntime(
        browser_backend=ExistingCdpBackend(
            "ws://127.0.0.1:9222/devtools/browser/test",
            session_id="session-a",
        )
    )

    session = asyncio.run(runtime.create_browser())
    asyncio.run(runtime.close_browser(session.id))

    snapshot = runtime.telemetry_snapshot()
    assert snapshot["actions"][0]["kind"] == "create_browser"
    assert snapshot["actions"][1]["kind"] == "close_browser"
    assert snapshot["used_runtime_assist"] is False


def _install_fake_lexmount(
    monkeypatch: pytest.MonkeyPatch,
    *,
    create_error_name: str | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "client_kwargs": {},
        "create_calls": [],
        "fork_calls": [],
        "context_delete_calls": [],
        "session_delete_calls": [],
        "session_close_calls": 0,
        "client_close_calls": 0,
    }

    class FakeAPIError(Exception):
        pass

    class FakeAuthenticationError(Exception):
        pass

    class FakeNetworkError(Exception):
        pass

    class FakeTimeoutError(Exception):
        pass

    class FakeValidationError(Exception):
        pass

    error_classes = {
        "APIError": FakeAPIError,
        "AuthenticationError": FakeAuthenticationError,
        "NetworkError": FakeNetworkError,
        "TimeoutError": FakeTimeoutError,
        "ValidationError": FakeValidationError,
    }

    class FakeSession:
        id = "session_123"
        session_id = "session_123"
        ws = "wss://cdp.lexmount.test/devtools"
        connect_url = None
        inspect_url = ""
        status = "active"
        browser_type = "chromium"
        created_at = "2026-05-19T00:00:00Z"

        def close(self) -> None:
            state["session_close_calls"] += 1

    class FakeSessions:
        def create(self, **kwargs: Any) -> FakeSession:
            state["create_calls"].append(kwargs)
            if create_error_name is not None:
                raise error_classes[create_error_name]("create failed")
            return FakeSession()

        def delete(self, *, session_id: str) -> None:
            state["session_delete_calls"].append(session_id)

        def list(self, *, status: str) -> Any:
            del status
            return SimpleNamespace(sessions=[])

    class FakeContexts:
        def fork(self, context_id: str) -> Any:
            state["fork_calls"].append(context_id)
            return SimpleNamespace(id="forked_ctx_456")

        def delete(self, context_id: str) -> None:
            state["context_delete_calls"].append(context_id)

    class FakeLexmount:
        def __init__(self, **kwargs: Any) -> None:
            state["client_kwargs"] = kwargs
            self.sessions = FakeSessions()
            self.contexts = FakeContexts()
            self.base_url = kwargs.get("base_url") or "https://api.lexmount.cn"
            self._http_client = SimpleNamespace(timeout=30)

        def close(self) -> None:
            state["client_close_calls"] += 1

    fake_lexmount = ModuleType("lexmount")
    setattr(fake_lexmount, "Lexmount", FakeLexmount)
    setattr(fake_lexmount, "APIError", FakeAPIError)
    setattr(fake_lexmount, "AuthenticationError", FakeAuthenticationError)
    setattr(fake_lexmount, "NetworkError", FakeNetworkError)
    setattr(fake_lexmount, "TimeoutError", FakeTimeoutError)
    setattr(fake_lexmount, "ValidationError", FakeValidationError)

    class SessionProxyConfig(dict[str, Any]):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(kwargs)

    fake_sessions = ModuleType("lexmount._sessions")
    setattr(fake_sessions, "SessionProxyConfig", SessionProxyConfig)

    monkeypatch.setitem(sys.modules, "lexmount", fake_lexmount)
    monkeypatch.setitem(sys.modules, "lexmount._sessions", fake_sessions)
    return state


def test_lexmount_backend_forks_context_and_normalizes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _install_fake_lexmount(monkeypatch)
    backend = LexmountBackend()

    session = asyncio.run(
        backend.create_browser(
            CreateBrowserRequest(
                lexmount_api_key="key",
                lexmount_project_id="project",
                lexmount_base_url="https://api.lexmount.cn",
                lexmount_base_context_id="base_ctx_123",
                lexmount_proxy={"server": "http://proxy.test:8080"},
                lexmount_verify_ssl=False,
            )
        )
    )

    assert state["client_kwargs"] == {
        "api_key": "key",
        "project_id": "project",
        "base_url": "https://api.lexmount.cn",
        "timeout": 60.0,
    }
    assert state["fork_calls"] == ["base_ctx_123"]
    assert state["create_calls"][0]["context"] == {
        "id": "forked_ctx_456",
        "mode": "read_write",
    }
    assert state["create_calls"][0]["proxy"] == {"server": "http://proxy.test:8080"}
    assert session.id == "session_123"
    assert session.cdp_url == "wss://cdp.lexmount.test/devtools"
    assert session.inspect_url == (
        "https://browser.lexmount.cn/browser_dev/index.html"
        "?session_id=session_123#api_host=api.lexmount.cn"
    )
    assert session.metadata["forked_context_id"] == "forked_ctx_456"

    asyncio.run(backend.close_browser(session.id))

    assert state["session_close_calls"] == 1
    assert state["session_delete_calls"] == ["session_123"]
    assert state["context_delete_calls"] == ["forked_ctx_456"]
    assert state["client_close_calls"] == 1


def test_lexmount_backend_cleans_client_and_fork_on_known_create_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _install_fake_lexmount(monkeypatch, create_error_name="NetworkError")
    backend = LexmountBackend()

    with pytest.raises(BrowserRuntimeError, match="Network error"):
        asyncio.run(
            backend.create_browser(
                CreateBrowserRequest(lexmount_base_context_id="base_ctx_123")
            )
        )

    assert state["fork_calls"] == ["base_ctx_123"]
    assert state["context_delete_calls"] == ["forked_ctx_456"]
    assert state["client_close_calls"] == 1
    assert backend.current_session_id is None
    assert backend.current_forked_context_id is None


def test_lexmount_backend_rejects_second_active_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_lexmount(monkeypatch)
    backend = LexmountBackend()

    session = asyncio.run(backend.create_browser(CreateBrowserRequest()))
    with pytest.raises(BrowserRuntimeError, match="already owns an active"):
        asyncio.run(backend.create_browser(CreateBrowserRequest()))

    asyncio.run(backend.close_browser(session.id))
