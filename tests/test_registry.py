from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lex_browser_runtime import AdapterEndpoint, AdapterRegistry, LexBrowserRuntime
from lex_browser_runtime.registry import default_adapters_dir, default_site_hints_path
from lex_browser_runtime.registry.utils import root_domain, task_domains


def _write_adapter(path: Path, domain: str, example_url: str) -> None:
    path.write_text(
        json.dumps(
            {
                "domain": domain,
                "endpoints": [
                    {
                        "domain": domain,
                        "url_pattern": re.escape(example_url),
                        "method": "GET",
                        "description": "Search endpoint",
                        "example_url": example_url,
                        "fetch_mode": "http",
                        "strategy": "search",
                        "output_contract": ["title", "url"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_root_domain_handles_common_two_part_tlds() -> None:
    assert root_domain("https://finance.sina.com.cn/roll") == "sina.com.cn"
    assert root_domain("sub.example.com") == "example.com"


def test_task_domains_only_extracts_explicit_urls() -> None:
    domains = task_domains("score 4.9 on https://www.example.com/path")

    assert "example.com" in domains
    assert "www.example.com" in domains
    assert "4.9" not in domains


def test_registry_matches_adapter_and_site_hint(tmp_path: Path) -> None:
    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()
    _write_adapter(
        adapters_dir / "example.com.json",
        "example.com",
        "https://api.example.com/search?q=test",
    )
    hints_path = tmp_path / "site_hints.yaml"
    hints_path.write_text(
        """
example.com:
  hints:
    - Prefer the public search endpoint before UI navigation.
  strategies:
    - name: example_search
      trigger: Search tasks
      confidence: auto
      actions:
        - type: api_call
          description: Call search endpoint
          url_template: https://api.example.com/search?q=<query>
          method: GET
          fetch_mode: http
""",
        encoding="utf-8",
    )

    registry = AdapterRegistry(adapters_dir=adapters_dir, site_hints_path=hints_path)
    match = registry.match(
        task="Open https://www.example.com and search for test",
        url="https://www.example.com",
    )

    assert match.domains == ["example.com", "www.example.com"]
    assert len(match.adapters) == 1
    assert len(match.site_notices) == 1
    assert match.site_notices["example.com"].strategies[0].name == "example_search"


def test_runtime_records_capability_match(tmp_path: Path) -> None:
    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()
    _write_adapter(
        adapters_dir / "example.com.json",
        "example.com",
        "https://api.example.com/search?q=test",
    )

    runtime = LexBrowserRuntime.from_paths(adapters_dir=adapters_dir)
    match = runtime.match_capabilities(task="Use https://www.example.com")
    snapshot = runtime.telemetry_snapshot()

    assert match.has_capabilities
    assert snapshot["matched_adapter_count"] == 1
    assert snapshot["actions"][0]["kind"] == "match_capabilities"


def test_registry_loads_packaged_runtime_contracts_by_default() -> None:
    registry = AdapterRegistry()

    assert registry.adapters_dir == default_adapters_dir()
    assert registry.site_hints_path == default_site_hints_path()
    assert registry.adapters_dir is not None
    assert registry.site_hints_path is not None

    match = registry.match(task="Use https://www.docin.com to search documents")

    assert match.has_capabilities
    assert any(endpoint.domain == "docin.com" for endpoint in match.adapters)
    assert any("search\\.do" in endpoint.url_pattern for endpoint in match.adapters)
    assert "docin.com" in match.site_notices

    gamespot_match = registry.match(
        task="Use https://www.gamespot.com to find a game review score"
    )

    assert gamespot_match.has_capabilities
    assert any(
        endpoint.domain == "gamespot.com" for endpoint in gamespot_match.adapters
    )
    assert any(
        "wp-json/wp/v2/search" in endpoint.url_pattern
        for endpoint in gamespot_match.adapters
    )
    assert "gamespot.com" in gamespot_match.site_notices


def test_registry_matches_packaged_site_hint_by_conservative_alias() -> None:
    registry = AdapterRegistry()

    match = registry.match(task='Search for "vintage camera" on eBay and rank by bids')

    assert "ebay.com" in match.site_notices
    assert any(
        strategy.name == "ebay_auction_ranked_cards_extract"
        for strategy in match.site_notices["ebay.com"].strategies
    )


def test_registry_env_paths_override_packaged_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapters_dir = tmp_path / "adapters"
    adapters_dir.mkdir()
    _write_adapter(
        adapters_dir / "example.com.json",
        "example.com",
        "https://api.example.com/search?q=test",
    )
    hints_path = tmp_path / "site_hints.yaml"
    hints_path.write_text(
        "example.com:\n  hints:\n    - Prefer the test fixture adapter.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LEX_BROWSER_RUNTIME_ADAPTERS_DIR", str(adapters_dir))
    monkeypatch.setenv("LEX_BROWSER_RUNTIME_SITE_HINTS_PATH", str(hints_path))

    registry = AdapterRegistry()
    match = registry.match(task="Use https://www.example.com")

    assert registry.adapters_dir == adapters_dir
    assert registry.site_hints_path == hints_path
    assert len(match.adapters) == 1
    assert "example.com" in match.site_notices


def test_adapter_endpoint_times_out_catastrophic_regex() -> None:
    endpoint = AdapterEndpoint(
        domain="example.com",
        url_pattern=r"(a+)+b",
        method="GET",
        description="Unsafe pattern fixture",
        example_url="https://example.com/search",
    )

    assert endpoint.matches("a" * 100_000) is False
