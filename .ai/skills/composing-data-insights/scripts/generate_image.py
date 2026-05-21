#!/usr/bin/env python3
"""Generate images from text prompts via an OpenAI-compatible API and save to disk.

Reads OPENAI_API_KEY (required) and OPENAI_BASE_URL (optional, defaults to
https://api.openai.com/v1) from the environment.
"""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

DEFAULT_MODEL = "gpt-image-1"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_SIZE = "1024x1024"
DEFAULT_TIMEOUT = 60.0

EXIT_OK = 0
EXIT_BAD_INPUT = 2
EXIT_HTTP_ERROR = 3
EXIT_NETWORK_ERROR = 4
EXIT_BAD_RESPONSE = 5


class GenerateError(Exception):
    """Base class. Subclasses set `code` to a process exit code."""

    code = 1


class BadInputError(GenerateError):
    code = EXIT_BAD_INPUT


class HTTPError(GenerateError):
    code = EXIT_HTTP_ERROR


class NetworkError(GenerateError):
    code = EXIT_NETWORK_ERROR


class BadResponseError(GenerateError):
    code = EXIT_BAD_RESPONSE


def expand_paths(output: Path, n: int) -> List[Path]:
    if output.suffix == "":
        output = output.with_suffix(".png")
    if n == 1:
        return [output]
    return [
        output.parent / f"{output.stem}-{i}{output.suffix}" for i in range(1, n + 1)
    ]


def materialize_item(item: dict, *, timeout: float) -> bytes:
    """Turn one image item from the API response into raw bytes.

    item is either {"b64_json": str} or {"url": str}.
    """
    if "b64_json" in item:
        return base64.b64decode(item["b64_json"])
    if "url" in item:
        image_url = item["url"]
        if not isinstance(image_url, str):
            raise BadResponseError("image URL must be a string")
        parsed = urllib.parse.urlparse(image_url)
        validate_image_url(parsed)
        # No Authorization header: OpenAI returns time-limited signed URLs that
        # reject extra auth headers. Internal gateways that require auth on the
        # secondary GET will surface as NetworkError; revisit only if observed.
        try:
            with urllib.request.urlopen(image_url, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.URLError as exc:
            raise NetworkError(f"failed to download image: {exc.reason}") from exc
    raise BadResponseError("response item has neither b64_json nor url")


def _validate_public_https_url(
    parsed: urllib.parse.ParseResult,
    *,
    label: str,
    error_cls: type[GenerateError],
) -> None:
    """Reject URL forms that can target local files or obvious private hosts."""

    if parsed.scheme != "https":
        raise error_cls(f"unsafe {label} URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise error_cls(f"{label} URL is missing a host")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost"} or hostname.endswith(".localhost"):
        raise error_cls(f"unsafe {label} URL host: {parsed.hostname!r}")

    try:
        address = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        return

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise error_cls(f"unsafe {label} URL host: {parsed.hostname!r}")


def validate_image_url(parsed: urllib.parse.ParseResult) -> None:
    _validate_public_https_url(
        parsed,
        label="image",
        error_cls=BadResponseError,
    )


def validate_base_url(base_url: str) -> None:
    parsed = urllib.parse.urlparse(base_url)
    _validate_public_https_url(
        parsed,
        label="base",
        error_cls=BadInputError,
    )


def request_images(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    size: str,
    n: int,
    timeout: float,
) -> List[dict]:
    validate_base_url(base_url)
    url = base_url.rstrip("/") + "/images/generations"
    body = json.dumps({"model": model, "prompt": prompt, "size": size, "n": n}).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        try:
            preview = exc.read()[:200].decode("utf-8", errors="replace")
        except Exception:
            preview = ""
        raise HTTPError(f"http {exc.code}: {preview}") from exc
    except urllib.error.URLError as exc:
        raise NetworkError(f"network error: {exc.reason}") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        preview = payload[:200].decode("utf-8", errors="replace")
        raise BadResponseError(f"non-JSON response: {preview}") from exc

    items = parsed.get("data") if isinstance(parsed, dict) else None
    if not isinstance(items, list) or not items:
        preview = payload[:200].decode("utf-8", errors="replace")
        raise BadResponseError(f"unexpected response shape: {preview}")
    return items


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Generate images via an OpenAI-compatible /v1/images/generations endpoint."
        ),
    )
    p.add_argument("--prompt", required=True, help="Text description of the image.")
    p.add_argument(
        "--output",
        required=True,
        type=Path,
        help=(
            "Output file path. Missing extension is filled with .png. "
            "Existing files are overwritten."
        ),
    )
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--size", default=DEFAULT_SIZE, help="WxH, e.g. 1024x1024.")
    p.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of images. n>1 expands output to <stem>-1, <stem>-2, ...",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Per-request timeout in seconds.",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "OPENAI_API_KEY is not set; configure it in your shell or .env",
            file=sys.stderr,
        )
        return EXIT_BAD_INPUT
    base_url = os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    try:
        validate_base_url(base_url)
    except GenerateError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code

    paths = expand_paths(args.output, args.n)

    try:
        items = request_images(
            base_url=base_url,
            api_key=api_key,
            model=args.model,
            prompt=args.prompt,
            size=args.size,
            n=args.n,
            timeout=args.timeout,
        )
    except GenerateError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code

    if len(items) != len(paths):
        print(
            f"server returned {len(items)} items, expected {len(paths)}",
            file=sys.stderr,
        )
        return EXIT_BAD_RESPONSE

    for item, path in zip(items, paths):
        try:
            data = materialize_item(item, timeout=args.timeout)
        except GenerateError as exc:
            print(str(exc), file=sys.stderr)
            return exc.code
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(path.resolve())

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
