"""Unit tests for generate_image.py — stdlib only, no network."""

import base64
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).with_name("generate_image.py")


def load_module():
    spec = importlib.util.spec_from_file_location("generate_image", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generate_image = load_module()
BadInputError = generate_image.BadInputError
BadResponseError = generate_image.BadResponseError
HTTPError = generate_image.HTTPError
NetworkError = generate_image.NetworkError
expand_paths = generate_image.expand_paths
main = generate_image.main
materialize_item = generate_image.materialize_item
request_images = generate_image.request_images
validate_base_url = generate_image.validate_base_url


@contextmanager
def env_overrides(**overrides):
    saved = {k: os.environ.get(k) for k in overrides}
    try:
        for k, v in overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _fake_response(payload_bytes: bytes):
    return BytesIO(payload_bytes)


class ExpandPathsTests(unittest.TestCase):
    def test_n1_with_extension_unchanged(self):
        self.assertEqual(
            expand_paths(Path("dir/foo.png"), 1),
            [Path("dir/foo.png")],
        )

    def test_n1_missing_extension_appends_png(self):
        self.assertEqual(
            expand_paths(Path("dir/foo"), 1),
            [Path("dir/foo.png")],
        )

    def test_n3_expands_with_index_and_keeps_extension(self):
        self.assertEqual(
            expand_paths(Path("dir/foo.png"), 3),
            [Path("dir/foo-1.png"), Path("dir/foo-2.png"), Path("dir/foo-3.png")],
        )

    def test_n3_with_missing_extension_still_appends_png(self):
        self.assertEqual(
            expand_paths(Path("dir/foo"), 3),
            [Path("dir/foo-1.png"), Path("dir/foo-2.png"), Path("dir/foo-3.png")],
        )


class MaterializeItemTests(unittest.TestCase):
    def test_b64_json_decoded(self):
        payload = b"\x89PNG\r\n\x1a\nFAKE"
        item = {"b64_json": base64.b64encode(payload).decode("ascii")}
        self.assertEqual(materialize_item(item, timeout=1.0), payload)

    def test_url_fetched_via_urlopen(self):
        payload = b"\x89PNG\r\n\x1a\nREMOTE"
        item = {"url": "https://example.invalid/image.png"}
        with patch(
            "generate_image.urllib.request.urlopen",
            return_value=_fake_response(payload),
        ) as mock_open:
            self.assertEqual(materialize_item(item, timeout=2.0), payload)
        mock_open.assert_called_once()
        # Second-GET must NOT carry an Authorization header (public signed URL).
        called_arg = mock_open.call_args.args[0]
        if hasattr(called_arg, "headers"):
            self.assertNotIn(
                "Authorization",
                {k.title() for k in called_arg.headers.keys()},
            )

    def test_neither_b64_nor_url_raises(self):
        with self.assertRaises(BadResponseError):
            materialize_item({"unexpected": "shape"}, timeout=1.0)

    def test_url_network_failure_raises(self):
        item = {"url": "https://example.invalid/x.png"}
        with patch(
            "generate_image.urllib.request.urlopen",
            side_effect=urllib.error.URLError("DNS fail"),
        ):
            with self.assertRaises(NetworkError):
                materialize_item(item, timeout=1.0)

    def test_non_https_url_rejected_before_urlopen(self):
        for url in (
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
        ):
            with self.subTest(url=url):
                with patch("generate_image.urllib.request.urlopen") as mock_open:
                    with self.assertRaises(BadResponseError):
                        materialize_item({"url": url}, timeout=1.0)
                mock_open.assert_not_called()

    def test_private_or_local_https_hosts_rejected_before_urlopen(self):
        for url in (
            "https://169.254.169.254/latest/meta-data/",
            "https://127.0.0.1/image.png",
            "https://10.0.0.1/image.png",
            "https://localhost/image.png",
            "https://foo.localhost/image.png",
            "https://[::1]/image.png",
            "https://[fe80::1%25eth0]/image.png",
        ):
            with self.subTest(url=url):
                with patch("generate_image.urllib.request.urlopen") as mock_open:
                    with self.assertRaises(BadResponseError):
                        materialize_item({"url": url}, timeout=1.0)
                mock_open.assert_not_called()

    def test_https_url_without_host_rejected_before_urlopen(self):
        with patch("generate_image.urllib.request.urlopen") as mock_open:
            with self.assertRaises(BadResponseError):
                materialize_item({"url": "https:///image.png"}, timeout=1.0)
        mock_open.assert_not_called()

    def test_non_string_url_rejected_before_urlopen(self):
        with patch("generate_image.urllib.request.urlopen") as mock_open:
            with self.assertRaises(BadResponseError):
                materialize_item({"url": None}, timeout=1.0)
        mock_open.assert_not_called()


class RequestImagesTests(unittest.TestCase):
    def test_happy_path_returns_data_list(self):
        body = json.dumps(
            {"data": [{"b64_json": "AA=="}, {"b64_json": "BB=="}]}
        ).encode()
        with patch(
            "generate_image.urllib.request.urlopen",
            return_value=_fake_response(body),
        ) as mock_open:
            items = request_images(
                base_url="https://gw.example/v1",
                api_key="k",
                model="m",
                prompt="p",
                size="1024x1024",
                n=2,
                timeout=5.0,
            )
        self.assertEqual(len(items), 2)
        sent_req = mock_open.call_args.args[0]
        self.assertEqual(sent_req.get_method(), "POST")
        self.assertEqual(sent_req.headers["Authorization"], "Bearer k")
        self.assertEqual(
            json.loads(sent_req.data),
            {"model": "m", "prompt": "p", "size": "1024x1024", "n": 2},
        )

    def test_http_error_raises_HTTPError(self):
        err = urllib.error.HTTPError(
            url="http://gw/v1/images/generations",
            code=500,
            msg="boom",
            hdrs=None,  # type: ignore[arg-type]
            fp=BytesIO(b'{"error":"server"}'),
        )
        with patch("generate_image.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(HTTPError) as ctx:
                request_images(
                    base_url="https://gw.invalid/v1",
                    api_key="k",
                    model="m",
                    prompt="p",
                    size="1024x1024",
                    n=1,
                    timeout=1.0,
                )
        self.assertIn("500", str(ctx.exception))
        self.assertNotIn("k", str(ctx.exception))  # key MUST NOT leak

    def test_url_error_raises_NetworkError(self):
        with patch(
            "generate_image.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with self.assertRaises(NetworkError):
                request_images(
                    base_url="https://gw.invalid/v1",
                    api_key="k",
                    model="m",
                    prompt="p",
                    size="1024x1024",
                    n=1,
                    timeout=1.0,
                )

    def test_malformed_json_raises_BadResponse(self):
        with patch(
            "generate_image.urllib.request.urlopen",
            return_value=_fake_response(b"not json"),
        ):
            with self.assertRaises(BadResponseError):
                request_images(
                    base_url="https://gw.invalid/v1",
                    api_key="k",
                    model="m",
                    prompt="p",
                    size="1024x1024",
                    n=1,
                    timeout=1.0,
                )

    def test_missing_data_field_raises_BadResponse(self):
        with patch(
            "generate_image.urllib.request.urlopen",
            return_value=_fake_response(b'{"unexpected": []}'),
        ):
            with self.assertRaises(BadResponseError):
                request_images(
                    base_url="https://gw.invalid/v1",
                    api_key="k",
                    model="m",
                    prompt="p",
                    size="1024x1024",
                    n=1,
                    timeout=1.0,
                )


class BaseUrlValidationTests(unittest.TestCase):
    def test_public_https_base_url_allowed(self):
        validate_base_url("https://api.openai.com/v1")

    def test_unsafe_base_urls_rejected(self):
        for url in (
            "http://api.openai.com/v1",
            "file:///tmp/socket",
            "https://169.254.169.254/v1",
            "https://127.0.0.1/v1",
            "https://localhost/v1",
            "https://[::1]/v1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(BadInputError):
                    validate_base_url(url)


class MainTests(unittest.TestCase):
    def test_missing_api_key_exits_2(self):
        with env_overrides(OPENAI_API_KEY=None):
            with tempfile.TemporaryDirectory() as td:
                rc = main(
                    [
                        "--prompt",
                        "x",
                        "--output",
                        str(Path(td) / "x.png"),
                    ]
                )
        self.assertEqual(rc, 2)

    def test_happy_path_writes_file_and_prints_path(self):
        png_bytes = b"\x89PNG\r\n\x1a\nFAKE-CONTENT"
        api_response = json.dumps(
            {"data": [{"b64_json": base64.b64encode(png_bytes).decode("ascii")}]}
        ).encode("utf-8")
        with env_overrides(
            OPENAI_API_KEY="k",
            OPENAI_BASE_URL="https://gw.example/v1",
        ):
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "sub" / "img"  # no extension, sub-dir not yet created
                with patch(
                    "generate_image.urllib.request.urlopen",
                    return_value=_fake_response(api_response),
                ):
                    rc = main(
                        [
                            "--prompt",
                            "futuristic city",
                            "--output",
                            str(out),
                        ]
                    )
                final = out.with_suffix(".png")
                self.assertEqual(rc, 0)
                self.assertTrue(final.exists())
                self.assertEqual(final.read_bytes(), png_bytes)

    def test_n3_writes_three_files(self):
        png = b"\x89PNG..."
        b64 = base64.b64encode(png).decode("ascii")
        api_response = json.dumps(
            {"data": [{"b64_json": b64}, {"b64_json": b64}, {"b64_json": b64}]}
        ).encode("utf-8")
        with env_overrides(
            OPENAI_API_KEY="k",
            OPENAI_BASE_URL="https://gw.example/v1",
        ):
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "img.png"
                with patch(
                    "generate_image.urllib.request.urlopen",
                    return_value=_fake_response(api_response),
                ):
                    rc = main(
                        [
                            "--prompt",
                            "x",
                            "--output",
                            str(out),
                            "--n",
                            "3",
                        ]
                    )
                self.assertEqual(rc, 0)
                for i in (1, 2, 3):
                    self.assertTrue((Path(td) / f"img-{i}.png").exists())

    def test_count_mismatch_returns_5(self):
        api_response = json.dumps({"data": [{"b64_json": "AA=="}]}).encode()
        with env_overrides(
            OPENAI_API_KEY="k",
            OPENAI_BASE_URL="https://gw.example/v1",
        ):
            with tempfile.TemporaryDirectory() as td:
                with patch(
                    "generate_image.urllib.request.urlopen",
                    return_value=_fake_response(api_response),
                ):
                    rc = main(
                        [
                            "--prompt",
                            "x",
                            "--output",
                            str(Path(td) / "img.png"),
                            "--n",
                            "2",
                        ]
                    )
        self.assertEqual(rc, 5)

    def test_unsafe_base_url_returns_bad_input_before_urlopen(self):
        with env_overrides(
            OPENAI_API_KEY="k",
            OPENAI_BASE_URL="http://169.254.169.254/v1",
        ):
            with tempfile.TemporaryDirectory() as td:
                with patch("generate_image.urllib.request.urlopen") as mock_open:
                    rc = main(
                        [
                            "--prompt",
                            "x",
                            "--output",
                            str(Path(td) / "img.png"),
                        ]
                    )
        self.assertEqual(rc, 2)
        mock_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
