from __future__ import annotations

import json
from pathlib import Path

from lex_browser_runtime.auth_contexts import (
    AuthContextEntry,
    AuthContextStore,
    default_auth_contexts_path,
    load_auth_context_store,
    save_auth_context_entry,
)


def test_default_auth_contexts_path_uses_home(monkeypatch) -> None:
    monkeypatch.setenv("HOME", "/tmp/runtime-home")
    monkeypatch.delenv("LEX_BROWSER_AUTH_CONTEXTS_FILE", raising=False)

    assert default_auth_contexts_path() == Path(
        "/tmp/runtime-home/.lex-browser-runtime/auth-contexts.json"
    )


def test_default_auth_contexts_path_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv(
        "LEX_BROWSER_AUTH_CONTEXTS_FILE",
        "/tmp/custom-auth-contexts.json",
    )

    assert default_auth_contexts_path() == Path("/tmp/custom-auth-contexts.json")


def test_load_missing_auth_context_file_returns_empty_store(tmp_path: Path) -> None:
    store = load_auth_context_store(tmp_path / "missing.json")

    assert store == AuthContextStore(contexts={})
    assert store.get("xiaohongshu") is None


def test_save_and_load_auth_context_entry(tmp_path: Path) -> None:
    path = tmp_path / "auth-contexts.json"

    save_auth_context_entry(
        path,
        "xiaohongshu",
        AuthContextEntry(
            context_id="ctx_xhs",
            login_url="https://www.xiaohongshu.com",
        ),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["contexts"]["xiaohongshu"]["context_id"] == "ctx_xhs"

    store = load_auth_context_store(path)
    entry = store.get("xiaohongshu")
    assert entry is not None
    assert entry.context_id == "ctx_xhs"
    assert entry.context_mode == "read_write"
    assert entry.login_url == "https://www.xiaohongshu.com"
