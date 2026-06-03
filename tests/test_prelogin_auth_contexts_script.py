from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    REPO_ROOT / "skills" / "lexmount-browser" / "scripts" / "prelogin-auth-contexts"
)


def _load_prelogin_script() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "prelogin_auth_contexts",
        str(SCRIPT_PATH),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_prelogin_reuses_saved_context_for_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_prelogin_script()
    auth_contexts_file = tmp_path / "auth-contexts.json"
    auth_contexts_file.write_text(
        json.dumps(
            {
                "version": 1,
                "contexts": {
                    "xiaohongshu": {
                        "context_id": "ctx_existing",
                        "context_mode": "read_write",
                        "login_url": "https://www.xiaohongshu.com",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_run_runtime(args: list[str]) -> dict[str, object]:
        calls.append(args)
        if args[:2] == ["context", "create"]:
            raise AssertionError("prelogin should reuse the saved context")
        if args[:2] == ["session", "create"]:
            assert "--context-id" in args
            assert args[args.index("--context-id") + 1] == "ctx_existing"
            return {
                "session": {
                    "session_id": "session_existing",
                    "inspect_url": "https://browser.lexmount.test/inspect",
                }
            }
        if args[:2] == ["action", "open-url"]:
            return {"ok": True}
        if args[:2] == ["action", "snapshot"]:
            return {"result": {"text": "logged in content"}}
        if args[:2] == ["session", "close"]:
            return {"ok": True}
        raise AssertionError(f"unexpected runtime args: {args}")

    monkeypatch.setattr(module, "_run_runtime", fake_run_runtime)
    monkeypatch.setattr(module, "input", lambda _prompt: "", raising=False)

    module._prelogin_source("xiaohongshu", auth_contexts_file)

    assert not any(args[:2] == ["context", "create"] for args in calls)
    payload = json.loads(auth_contexts_file.read_text(encoding="utf-8"))
    assert payload["contexts"]["xiaohongshu"]["context_id"] == "ctx_existing"
