from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("render_report.py")


def load_module():
    spec = importlib.util.spec_from_file_location("render_report", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_model() -> dict:
    return {
        "period": {"start": "2026-05-04", "end": "2026-05-10"},
        "scope": {"owner": "acme", "project": "Launch"},
        "projects": [
            {"title": "Launch", "url": "https://github.com/orgs/acme/projects/1"}
        ],
        "items": [
            {
                "type": "issue",
                "title": "Ship onboarding",
                "url": "https://github.com/acme/app/issues/1",
                "repository": "acme/app",
                "state": "CLOSED",
                "fields": {"Status": "Done"},
            },
            {
                "type": "pull_request",
                "title": "Improve checkout",
                "url": "https://github.com/acme/app/pull/2",
                "repository": "acme/app",
                "state": "MERGED",
                "fields": {"Status": "Review"},
            },
        ],
        "people": {
            "ada": {"closed_items": 1, "reviews": 2},
            "lin": {"pull_requests": 1, "commits": 3},
        },
        "metrics": {"total_items": 2, "closed_items": 2, "pull_requests": 1},
        "caveats": ["1 redacted project item was not visible."],
    }


def test_renders_management_markdown_with_coverage_caveats() -> None:
    module = load_module()

    markdown = module.render_markdown(sample_model(), view="management")

    assert "# GitHub Activity Report" in markdown
    assert "2026-05-04 to 2026-05-10" in markdown
    assert "## Summary" in markdown
    assert "## Completed Work" in markdown
    assert "Ship onboarding" in markdown
    assert "## People Activity Signals" in markdown
    assert "not a performance ranking" in markdown
    assert "## Data Coverage / Limitations" in markdown
    assert "redacted project item" in markdown


def test_renders_self_contained_html_without_remote_assets() -> None:
    module = load_module()

    html = module.render_html(sample_model(), view="engineering")

    assert "<!doctype html>" in html.lower()
    assert "GitHub Activity Report" in html
    assert "Engineering Signals" in html
    assert "Data Coverage / Limitations" in html
    assert "https://cdn" not in html
    assert "<script" not in html.lower()


def test_html_links_completed_items_to_visible_github_evidence() -> None:
    module = load_module()

    html = module.render_html(sample_model(), view="management")

    assert '<a href="https://github.com/acme/app/issues/1">' in html
    assert "Ship onboarding" in html


def test_html_wraps_list_items_in_unordered_list() -> None:
    module = load_module()

    html = module.render_html(sample_model(), view="management")

    assert "<ul>" in html
    assert "</ul>" in html
    ul_open = html.index("<ul>")
    first_li = html.index("<li>")
    assert ul_open < first_li
    last_ul_close = html.rindex("</ul>")
    last_li_close = html.rindex("</li>")
    assert last_li_close < last_ul_close
