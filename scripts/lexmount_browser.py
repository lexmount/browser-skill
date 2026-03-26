#!/usr/bin/env python3
"""Helper CLI for Lexmount browser contexts and sessions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SDK_SRC = REPO_ROOT / "lexmount-python-sdk" / "src"

if SDK_SRC.exists():
    sys.path.insert(0, str(SDK_SRC))

if TYPE_CHECKING:
    from lexmount import Lexmount


REQUIRED_ENV_VARS = ("LEXMOUNT_API_KEY", "LEXMOUNT_PROJECT_ID")


def _missing_env_vars() -> list[str]:
    return [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]


def _json_dump(payload: Dict[str, Any], exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    raise SystemExit(exit_code)


def _load_sdk():
    try:
        from lexmount import Lexmount
        from lexmount.exceptions import LexmountError, ValidationError
    except Exception as exc:  # pragma: no cover - import failure path
        _json_dump(
            {
                "ok": False,
                "error": "sdk_import_failed",
                "message": (
                    "Failed to import local lexmount SDK. Ensure "
                    "lexmount-python-sdk and its Python dependencies are available."
                ),
                "details": str(exc),
                "sdk_src": str(SDK_SRC),
            },
            exit_code=1,
        )

    return Lexmount, LexmountError, ValidationError


def _build_client() -> "Lexmount":
    Lexmount, _, ValidationError = _load_sdk()

    missing = _missing_env_vars()
    if missing:
        _json_dump(
            {
                "ok": False,
                "error": "missing_env",
                "message": "Missing required environment variables.",
                "missing": missing,
            },
            exit_code=1,
        )

    try:
        return Lexmount()
    except ValidationError as exc:
        _json_dump(
            {
                "ok": False,
                "error": "validation_error",
                "message": str(exc),
            },
            exit_code=1,
        )


def _normalize_context_mode(value: str) -> str:
    if value not in {"read_write", "read_only"}:
        raise argparse.ArgumentTypeError("context mode must be read_write or read_only")
    return value


def _normalize_browser_mode(value: str) -> str:
    if value not in {"normal", "light", "chrome-light-docker"}:
        raise argparse.ArgumentTypeError("browser mode must be normal, light, or chrome-light-docker")
    return value


def cmd_prepare(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        context_id = args.context_id
        created_context = False

        if not context_id:
            context = client.contexts.create(metadata={"created_by": "codex-browser-skill"})
            context_id = context.id
            created_context = True

        session = client.sessions.create(
            browser_mode=args.browser_mode,
            context={"id": context_id, "mode": args.context_mode},
        )

        _json_dump(
            {
                "ok": True,
                "mode": "sdk",
                "base_url": client.base_url,
                "project_id": client.project_id,
                "context_id": context_id,
                "created_context": created_context,
                "context_mode": args.context_mode,
                "browser_mode": args.browser_mode,
                "session_id": session.id,
                "connect_url": session.connect_url,
                "inspect_url": session.inspect_url,
                "container_id": session.container_id,
            }
        )
    except LexmountError as exc:
        _json_dump(
            {
                "ok": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
            exit_code=1,
        )


def cmd_list_contexts(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        response = client.contexts.list(limit=args.limit)
        contexts = [
            {
                "id": item.id,
                "status": item.status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in response
        ]
        _json_dump(
            {
                "ok": True,
                "count": len(contexts),
                "contexts": contexts,
            }
        )
    except LexmountError as exc:
        _json_dump(
            {
                "ok": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
            exit_code=1,
        )


def cmd_close_session(args: argparse.Namespace) -> None:
    client = _build_client()
    _, LexmountError, _ = _load_sdk()

    try:
        client.sessions.delete(session_id=args.session_id)
        _json_dump(
            {
                "ok": True,
                "session_id": args.session_id,
                "closed": True,
            }
        )
    except LexmountError as exc:
        _json_dump(
            {
                "ok": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
                "session_id": args.session_id,
            },
            exit_code=1,
        )


def cmd_direct_url(args: argparse.Namespace) -> None:
    missing = _missing_env_vars()
    if missing:
        _json_dump(
            {
                "ok": False,
                "error": "missing_env",
                "message": "Missing required environment variables.",
                "missing": missing,
            },
            exit_code=1,
        )

    base_url = os.environ.get("LEXMOUNT_BASE_URL", "https://api.lexmount.cn").rstrip("/")
    ws_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    url = (
        f"{ws_base}/connection?project_id={os.environ['LEXMOUNT_PROJECT_ID']}"
        f"&api_key={os.environ['LEXMOUNT_API_KEY']}"
    )

    _json_dump(
        {
            "ok": True,
            "mode": "direct",
            "connect_url": url,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lexmount browser helper for Codex skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Create or reuse a context, then create a session")
    prepare.add_argument("--context-id", help="Reuse an existing context")
    prepare.add_argument("--context-mode", default="read_write", type=_normalize_context_mode)
    prepare.add_argument("--browser-mode", default="normal", type=_normalize_browser_mode)
    prepare.set_defaults(func=cmd_prepare)

    list_contexts = subparsers.add_parser("list-contexts", help="List contexts for the current project")
    list_contexts.add_argument("--limit", type=int, default=20)
    list_contexts.set_defaults(func=cmd_list_contexts)

    close_session = subparsers.add_parser("close-session", help="Close a browser session")
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
