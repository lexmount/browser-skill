from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("normalize_activity.py")


def load_module():
    spec = importlib.util.spec_from_file_location("normalize_activity", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalizes_project_items_and_preserves_redaction_caveats() -> None:
    module = load_module()
    raw = {
        "period": {"start": "2026-05-04", "end": "2026-05-10"},
        "scope": {"owner": "acme", "project": "Launch"},
        "projects": [
            {
                "id": "PVT_1",
                "title": "Launch",
                "url": "https://github.com/orgs/acme/projects/1",
            }
        ],
        "items": [
            {
                "id": "PVTI_issue",
                "content": {
                    "type": "Issue",
                    "title": "Ship onboarding",
                    "url": "https://github.com/acme/app/issues/1",
                    "repository": "acme/app",
                    "state": "CLOSED",
                    "assignees": ["ada"],
                    "labels": ["feature"],
                },
                "field_values": [
                    {"field": "Status", "value": "Done"},
                    {"field": "Iteration", "value": "May W2"},
                ],
                "activity": [
                    {
                        "type": "closed",
                        "actor": "ada",
                        "created_at": "2026-05-06T00:00:00Z",
                    }
                ],
            },
            {
                "id": "PVTI_pr",
                "content": {
                    "type": "PullRequest",
                    "title": "Improve checkout",
                    "url": "https://github.com/acme/app/pull/2",
                    "repository": "acme/app",
                    "state": "MERGED",
                    "author": "lin",
                    "stats": {"additions": 10, "deletions": 2, "changed_files": 1},
                },
                "field_values": [
                    {"field": "Status", "value": "Review"},
                    {"field": "Status", "value": "In Review"},
                ],
                "reviews": [
                    {
                        "author": "ada",
                        "state": "APPROVED",
                        "submitted_at": "2026-05-06T00:00:00Z",
                    }
                ],
                "commits": [
                    {
                        "author": "lin",
                        "sha": "abc123",
                        "authored_at": "2026-05-07T00:00:00Z",
                    }
                ],
            },
            {
                "id": "PVTI_draft",
                "content": {"type": "DraftIssue", "title": "Draft rollout note"},
                "field_values": [{"field": "Status", "value": "Todo"}],
            },
            {"id": "PVTI_redacted", "content": {"type": "REDACTED"}},
        ],
    }

    model = module.normalize_activity(raw)

    assert model["period"] == {"start": "2026-05-04", "end": "2026-05-10"}
    assert model["scope"]["owner"] == "acme"
    assert model["metrics"]["total_items"] == 4
    assert model["metrics"]["closed_items"] == 2
    assert model["items"][0]["type"] == "issue"
    assert model["items"][1]["type"] == "pull_request"
    assert model["items"][1]["stats"] == {
        "additions": 10,
        "deletions": 2,
        "changed_files": 1,
    }
    assert model["items"][2]["type"] == "draft_issue"
    assert model["items"][3]["type"] == "redacted"
    assert model["metrics"]["additions"] == 10
    assert model["metrics"]["deletions"] == 2
    assert model["metrics"]["changed_files"] == 1
    assert model["people"]["ada"]["closed_items"] == 1
    assert model["people"]["ada"]["reviews"] == 1
    assert model["people"]["lin"]["pull_requests"] == 1
    caveats = "\n".join(model["caveats"])
    assert "field conflict" in caveats
    assert "redacted" in caveats
    assert "Draft issue" in caveats
    assert "commit stats unavailable" in caveats


def test_missing_required_scope_fails_fast() -> None:
    module = load_module()

    try:
        module.normalize_activity(
            {"period": {"start": "2026-05-04", "end": "2026-05-10"}}
        )
    except ValueError as exc:
        assert "scope" in str(exc)
    else:
        raise AssertionError("normalize_activity should require scope")


def test_invalid_period_dates_fail_fast() -> None:
    module = load_module()
    raw = {
        "period": {"start": "bad-date", "end": "2026-05-10"},
        "scope": {"owner": "acme", "project": "Launch"},
        "items": [],
    }

    try:
        module.normalize_activity(raw)
    except ValueError as exc:
        assert "period.start" in str(exc)
    else:
        raise AssertionError("normalize_activity should reject invalid period dates")


def test_invalid_entry_timestamp_is_reported_as_coverage_caveat_and_excluded() -> None:
    module = load_module()
    raw = {
        "period": {"start": "2026-05-04", "end": "2026-05-10"},
        "scope": {"owner": "acme", "project": "Launch"},
        "items": [
            {
                "id": "PVTI_issue",
                "content": {
                    "type": "Issue",
                    "title": "Malformed activity",
                    "state": "CLOSED",
                },
                "activity": [
                    {"type": "closed", "actor": "ada", "created_at": "not-a-date"}
                ],
            }
        ],
    }

    model = module.normalize_activity(raw)

    assert model["metrics"]["total_items"] == 0
    assert "ada" not in model["people"]
    assert "invalid activity timestamp for item PVTI_issue" in "\n".join(
        model["caveats"]
    )


def test_filters_activity_reviews_and_commits_to_period() -> None:
    module = load_module()
    raw = {
        "period": {"start": "2026-05-04", "end": "2026-05-10"},
        "scope": {"owner": "acme", "project": "Launch"},
        "items": [
            {
                "id": "PVTI_pr",
                "content": {
                    "type": "PullRequest",
                    "title": "Improve checkout",
                    "url": "https://github.com/acme/app/pull/2",
                    "repository": "acme/app",
                    "state": "MERGED",
                    "author": "lin",
                },
                "field_values": [{"field": "Status", "value": "Done"}],
                "activity": [
                    {
                        "type": "updated",
                        "actor": "lin",
                        "created_at": "2026-05-05T00:00:00Z",
                    },
                    {
                        "type": "updated",
                        "actor": "lin",
                        "created_at": "2026-04-30T00:00:00Z",
                    },
                ],
                "reviews": [
                    {
                        "author": "ada",
                        "state": "APPROVED",
                        "submitted_at": "2026-05-06T00:00:00Z",
                    },
                    {
                        "author": "bea",
                        "state": "COMMENTED",
                        "submitted_at": "2026-04-30T00:00:00Z",
                    },
                ],
                "commits": [
                    {
                        "author": "lin",
                        "sha": "in-window",
                        "authored_at": "2026-05-07T00:00:00Z",
                        "additions": 3,
                        "deletions": 1,
                    },
                    {
                        "author": "max",
                        "sha": "old",
                        "authored_at": "2026-04-30T00:00:00Z",
                        "additions": 10,
                        "deletions": 2,
                    },
                ],
            }
        ],
    }

    model = module.normalize_activity(raw)

    assert model["items"][0]["activity"] == [
        {"type": "updated", "actor": "lin", "created_at": "2026-05-05T00:00:00Z"}
    ]
    assert model["people"]["ada"]["reviews"] == 1
    assert "bea" not in model["people"]
    assert model["people"]["lin"]["commits"] == 1
    assert "max" not in model["people"]
    caveats = "\n".join(model["caveats"])
    assert "outside report period" in caveats
