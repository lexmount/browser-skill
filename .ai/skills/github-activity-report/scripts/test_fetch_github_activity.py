from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).with_name("fetch_github_activity.py")


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_github_activity", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fetches_project_items_into_raw_activity_payload() -> None:
    module = load_module()
    calls = []

    def fake_graphql(query, variables):
        calls.append((query, variables))
        return {
            "data": {
                "organization": {
                    "projectV2": {
                        "id": "PVT_1",
                        "title": "Launch",
                        "url": "https://github.com/orgs/acme/projects/1",
                        "items": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "id": "PVTI_pr",
                                    "type": "ISSUE",
                                    "content": {
                                        "__typename": "PullRequest",
                                        "title": "Ship checkout",
                                        "url": "https://github.com/acme/app/pull/2",
                                        "state": "MERGED",
                                        "createdAt": "2026-05-01T00:00:00Z",
                                        "updatedAt": "2026-05-02T00:00:00Z",
                                        "closedAt": "2026-05-03T00:00:00Z",
                                        "mergedAt": "2026-05-03T00:00:00Z",
                                        "additions": 10,
                                        "deletions": 2,
                                        "changedFiles": 1,
                                        "author": {"login": "lin"},
                                        "repository": {"nameWithOwner": "acme/app"},
                                        "assignees": {
                                            "pageInfo": {
                                                "hasNextPage": True,
                                                "endCursor": "assignee-cursor",
                                            },
                                            "nodes": [{"login": "ada"}],
                                        },
                                        "labels": {
                                            "pageInfo": {
                                                "hasNextPage": True,
                                                "endCursor": "label-cursor",
                                            },
                                            "nodes": [{"name": "feature"}],
                                        },
                                        "reviews": {
                                            "pageInfo": {
                                                "hasNextPage": True,
                                                "endCursor": "review-cursor",
                                            },
                                            "nodes": [
                                                {
                                                    "state": "APPROVED",
                                                    "submittedAt": "2026-05-02T00:00:00Z",
                                                    "author": {"login": "ada"},
                                                }
                                            ],
                                        },
                                        "commits": {
                                            "pageInfo": {
                                                "hasNextPage": True,
                                                "endCursor": "commit-cursor",
                                            },
                                            "nodes": [
                                                {
                                                    "commit": {
                                                        "oid": "abc123",
                                                        "authoredDate": "2026-05-01T00:00:00Z",
                                                        "author": {
                                                            "user": {"login": "lin"},
                                                            "name": "Lin",
                                                        },
                                                    }
                                                }
                                            ],
                                        },
                                    },
                                    "fieldValues": {
                                        "pageInfo": {
                                            "hasNextPage": True,
                                            "endCursor": "field-cursor",
                                        },
                                        "nodes": [
                                            {
                                                "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                                "name": "Done",
                                                "field": {"name": "Status"},
                                            },
                                            {
                                                "__typename": "ProjectV2ItemFieldIterationValue",
                                                "title": "May W2",
                                                "startDate": "2026-05-04",
                                                "duration": 7,
                                                "field": {"name": "Iteration"},
                                            },
                                            {
                                                "__typename": "ProjectV2ItemFieldUserValue",
                                                "users": {
                                                    "pageInfo": {
                                                        "hasNextPage": True,
                                                        "endCursor": "users-cursor",
                                                    },
                                                    "nodes": [{"login": "lin"}],
                                                },
                                                "field": {"name": "Contributors"},
                                            },
                                        ],
                                    },
                                },
                                {
                                    "id": "PVTI_hidden",
                                    "type": "REDACTED",
                                    "content": None,
                                    "fieldValues": {"nodes": []},
                                },
                            ],
                        },
                    }
                },
                "user": None,
            }
        }

    module.run_gh_graphql = fake_graphql
    payload = module.fetch_project_activity(
        module.FetchArgs(
            owner="acme",
            project_number=1,
            start="2026-05-04",
            end="2026-05-10",
        )
    )

    assert calls[0][1] == {"owner": "acme", "number": 1, "itemCursor": None}
    query = calls[0][0]
    assert "reviews(first: 50)" in query
    assert "commits(first: 50)" in query
    assert "fieldValues(first: 50)" in query
    assert "assignees(first: 20)" in query
    assert "labels(first: 20)" in query
    assert "users(first: 20)" in query
    assert query.count("pageInfo") >= 10
    assert payload["scope"] == {
        "owner": "acme",
        "project_number": 1,
        "project": "Launch",
    }
    assert payload["projects"] == [
        {
            "id": "PVT_1",
            "title": "Launch",
            "url": "https://github.com/orgs/acme/projects/1",
        }
    ]
    assert payload["items"][0]["content"]["type"] == "PullRequest"
    assert payload["items"][0]["content"]["repository"] == "acme/app"
    assert payload["items"][0]["content"]["stats"] == {
        "additions": 10,
        "deletions": 2,
        "changed_files": 1,
    }
    assert payload["items"][0]["field_values"] == [
        {"field": "Status", "value": "Done"},
        {"field": "Iteration", "value": "May W2"},
        {"field": "Contributors", "value": ["lin"]},
    ]
    assert payload["items"][0]["coverage_caveats"] == [
        "field values may be incomplete for item PVTI_pr; first page ended at field-cursor",
        "assignees may be incomplete for item PVTI_pr; first page ended at assignee-cursor",
        "labels may be incomplete for item PVTI_pr; first page ended at label-cursor",
        "reviews may be incomplete for item PVTI_pr; first page ended at review-cursor",
        "commits may be incomplete for item PVTI_pr; first page ended at commit-cursor",
        "users may be incomplete for field Contributors on item PVTI_pr; first page ended at users-cursor",
    ]
    assert payload["items"][0]["reviews"] == [
        {
            "author": "ada",
            "state": "APPROVED",
            "submitted_at": "2026-05-02T00:00:00Z",
        }
    ]
    assert payload["items"][0]["commits"] == [
        {"sha": "abc123", "author": "lin", "authored_at": "2026-05-01T00:00:00Z"}
    ]
    assert payload["items"][1] == {
        "id": "PVTI_hidden",
        "content": {"type": "REDACTED"},
    }


def test_missing_owner_project_fails_fast() -> None:
    module = load_module()
    module.run_gh_graphql = lambda query, variables: {
        "data": {"organization": None, "user": None}
    }

    try:
        module.fetch_project_activity(
            module.FetchArgs(
                owner="missing",
                project_number=99,
                start="2026-05-04",
                end="2026-05-10",
            )
        )
    except module.FetchError as exc:
        assert "owner was not found" in str(exc)
    else:
        raise AssertionError("missing owner should fail")


def test_run_gh_graphql_uses_string_flag_for_owner_and_cursor() -> None:
    module = load_module()

    captured = {}

    class FakeCompleted:
        stdout = json.dumps({"data": {"organization": None, "user": None}})
        stderr = ""

    def fake_subprocess_run(command, check, capture_output, text):
        captured["command"] = command
        return FakeCompleted()

    with patch.object(module.subprocess, "run", fake_subprocess_run):
        module.run_gh_graphql(
            "query($owner: String!, $number: Int!, $itemCursor: String) {}",
            {"owner": "42", "number": 1, "itemCursor": "cursor-x"},
        )

    command = captured["command"]
    assert "-f" in command
    owner_index = command.index("owner=42")
    assert command[owner_index - 1] == "-f"
    cursor_index = command.index("itemCursor=cursor-x")
    assert command[cursor_index - 1] == "-f"
    number_index = command.index("number=1")
    assert command[number_index - 1] == "-F"


def test_run_gh_graphql_raises_on_graphql_errors() -> None:
    module = load_module()

    class FakeCompleted:
        stdout = json.dumps(
            {
                "data": {"organization": None},
                "errors": [{"message": "permission denied for projectV2"}],
            }
        )
        stderr = ""

    def fake_subprocess_run(command, check, capture_output, text):
        return FakeCompleted()

    with patch.object(module.subprocess, "run", fake_subprocess_run):
        try:
            module.run_gh_graphql("query {}", {"owner": "acme"})
        except module.FetchError as exc:
            assert "permission denied for projectV2" in str(exc)
        else:
            raise AssertionError("graphql errors should surface as FetchError")
