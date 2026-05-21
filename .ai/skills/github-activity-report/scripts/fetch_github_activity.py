"""Fetch read-only GitHub Projects v2 activity through GitHub CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


PROJECT_ITEMS_QUERY = """
query($owner: String!, $number: Int!, $itemCursor: String) {
  organization(login: $owner) {
    projectV2(number: $number) {
      ...ProjectFields
    }
  }
  user(login: $owner) {
    projectV2(number: $number) {
      ...ProjectFields
    }
  }
}

fragment ProjectFields on ProjectV2 {
  id
  title
  url
  items(first: 100, after: $itemCursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      id
      type
      content {
        __typename
        ... on Issue {
          title
          url
          state
          createdAt
          updatedAt
          closedAt
          author {
            login
          }
          repository {
            nameWithOwner
          }
          assignees(first: 20) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              login
            }
          }
          labels(first: 20) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              name
            }
          }
        }
        ... on PullRequest {
          title
          url
          state
          createdAt
          updatedAt
          closedAt
          mergedAt
          additions
          deletions
          changedFiles
          author {
            login
          }
          repository {
            nameWithOwner
          }
          assignees(first: 20) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              login
            }
          }
          labels(first: 20) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              name
            }
          }
          reviews(first: 50) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              state
              submittedAt
              author {
                login
              }
            }
          }
          commits(first: 50) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              commit {
                oid
                authoredDate
                author {
                  user {
                    login
                  }
                  name
                }
              }
            }
          }
        }
        ... on DraftIssue {
          title
          createdAt
          updatedAt
          assignees(first: 20) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              login
            }
          }
        }
      }
      fieldValues(first: 50) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          __typename
          ... on ProjectV2ItemFieldTextValue {
            text
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldSingleSelectValue {
            name
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldIterationValue {
            title
            startDate
            duration
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldDateValue {
            date
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldNumberValue {
            number
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldUserValue {
            users(first: 20) {
              pageInfo {
                hasNextPage
                endCursor
              }
              nodes {
                login
              }
            }
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldMilestoneValue {
            milestone {
              title
            }
            field {
              ...FieldName
            }
          }
          ... on ProjectV2ItemFieldRepositoryValue {
            repository {
              nameWithOwner
            }
            field {
              ...FieldName
            }
          }
        }
      }
    }
  }
}

fragment FieldName on ProjectV2FieldCommon {
  name
}
"""


@dataclass(frozen=True)
class FetchArgs:
    owner: str
    project_number: int
    start: str
    end: str


class FetchError(Exception):
    """Raised when GitHub data cannot be fetched or parsed."""


STRING_VARIABLES = {"owner", "itemCursor"}


def run_gh_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Run `gh api graphql` and return parsed JSON."""

    command = ["gh", "api", "graphql", "-f", f"query={query}"]
    for name, value in variables.items():
        if value is None:
            continue
        flag = "-f" if name in STRING_VARIABLES else "-F"
        command.extend([flag, f"{name}={value}"])

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise FetchError("GitHub CLI `gh` is required") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip()
        raise FetchError(f"gh api graphql failed: {detail}") from exc

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise FetchError("gh api graphql returned non-JSON output") from exc

    if not isinstance(payload, dict):
        raise FetchError("gh api graphql returned an unexpected JSON shape")

    errors = payload.get("errors")
    if errors:
        messages = [
            str(err.get("message", err)) if isinstance(err, dict) else str(err)
            for err in errors
        ]
        raise FetchError("gh api graphql reported errors: " + "; ".join(messages))

    return payload


def fetch_project_activity(args: FetchArgs) -> dict[str, Any]:
    """Fetch a GitHub Projects v2 raw activity payload."""

    items: list[dict[str, Any]] = []
    project_metadata: dict[str, Any] | None = None
    cursor: str | None = None

    while True:
        response = run_gh_graphql(
            PROJECT_ITEMS_QUERY,
            {
                "owner": args.owner,
                "number": args.project_number,
                "itemCursor": cursor,
            },
        )
        project = _extract_project(response)
        if project_metadata is None:
            project_metadata = {
                "id": project["id"],
                "title": project["title"],
                "url": project["url"],
            }

        item_connection = project["items"]
        for node in item_connection["nodes"]:
            items.append(_normalize_project_item(node))

        page_info = item_connection["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    if project_metadata is None:
        raise FetchError("project was not returned by GitHub")

    return {
        "period": {"start": args.start, "end": args.end},
        "scope": {
            "owner": args.owner,
            "project_number": args.project_number,
            "project": project_metadata["title"],
        },
        "projects": [project_metadata],
        "items": items,
    }


def _extract_project(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, dict):
        raise FetchError("GraphQL response is missing data")

    owner_payload = data.get("organization") or data.get("user")
    if not isinstance(owner_payload, dict):
        raise FetchError("owner was not found as a GitHub organization or user")

    project = owner_payload.get("projectV2")
    if not isinstance(project, dict):
        raise FetchError("Project v2 was not found for the requested owner and number")
    return project


def _normalize_project_item(node: dict[str, Any]) -> dict[str, Any]:
    content = node.get("content")
    if not isinstance(content, dict):
        return {"id": node["id"], "content": {"type": "REDACTED"}}

    content_type = content["__typename"]
    item = {
        "id": node["id"],
        "content": _normalize_content(content_type, content),
        "field_values": _normalize_field_values(node["fieldValues"]["nodes"]),
        "activity": _activity_from_content(content_type, content),
        "reviews": _normalize_reviews(content),
        "commits": _normalize_commits(content),
    }
    caveats = _coverage_caveats(node["id"], node.get("fieldValues"), content)
    if caveats:
        item["coverage_caveats"] = caveats
    return item


def _coverage_caveats(
    item_id: str,
    field_values: Any,
    content: dict[str, Any],
) -> list[str]:
    caveats: list[str] = []
    _append_page_caveat(caveats, item_id, "field values", field_values)
    _append_page_caveat(caveats, item_id, "assignees", content.get("assignees"))
    _append_page_caveat(caveats, item_id, "labels", content.get("labels"))
    _append_page_caveat(caveats, item_id, "reviews", content.get("reviews"))
    _append_page_caveat(caveats, item_id, "commits", content.get("commits"))
    _append_field_user_caveats(caveats, item_id, field_values)
    return caveats


def _append_page_caveat(
    caveats: list[str],
    item_id: str,
    label: str,
    connection: Any,
) -> None:
    if not isinstance(connection, dict):
        return
    page_info = connection.get("pageInfo")
    if not isinstance(page_info, dict) or not page_info.get("hasNextPage"):
        return
    end_cursor = page_info.get("endCursor") or "<unknown cursor>"
    caveats.append(
        f"{label} may be incomplete for item {item_id}; first page ended at {end_cursor}"
    )


def _append_field_user_caveats(
    caveats: list[str],
    item_id: str,
    field_values: Any,
) -> None:
    if not isinstance(field_values, dict):
        return
    for node in field_values.get("nodes", []):
        if (
            not isinstance(node, dict)
            or node.get("__typename") != "ProjectV2ItemFieldUserValue"
        ):
            continue
        users = node.get("users")
        if not isinstance(users, dict):
            continue
        page_info = users.get("pageInfo")
        if not isinstance(page_info, dict) or not page_info.get("hasNextPage"):
            continue
        field = node.get("field")
        field_name = field.get("name") if isinstance(field, dict) else "<unknown field>"
        end_cursor = page_info.get("endCursor") or "<unknown cursor>"
        caveats.append(
            "users may be incomplete for field "
            f"{field_name} on item {item_id}; first page ended at {end_cursor}"
        )


def _normalize_content(content_type: str, content: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "type": content_type,
        "title": content.get("title"),
        "url": content.get("url"),
        "state": content.get("state"),
        "author": _login(content.get("author")),
        "repository": _repository_name(content.get("repository")),
        "assignees": _node_logins(content.get("assignees")),
        "labels": _label_names(content.get("labels")),
    }
    if content_type == "PullRequest":
        normalized["stats"] = _pull_request_stats(content)
    return {key: value for key, value in normalized.items() if value is not None}


def _pull_request_stats(content: dict[str, Any]) -> dict[str, int]:
    stats: dict[str, int] = {}
    for source_key, target_key in (
        ("additions", "additions"),
        ("deletions", "deletions"),
        ("changedFiles", "changed_files"),
    ):
        value = content.get(source_key)
        if isinstance(value, int):
            stats[target_key] = value
    return stats


def _normalize_field_values(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for node in nodes:
        field = node.get("field")
        if not isinstance(field, dict) or not field.get("name"):
            continue
        value = _field_value(node)
        if value is None:
            continue
        values.append({"field": field["name"], "value": value})
    return values


def _field_value(node: dict[str, Any]) -> Any:
    typename = node["__typename"]
    if typename == "ProjectV2ItemFieldTextValue":
        return node.get("text")
    if typename == "ProjectV2ItemFieldSingleSelectValue":
        return node.get("name")
    if typename == "ProjectV2ItemFieldIterationValue":
        return node.get("title")
    if typename == "ProjectV2ItemFieldDateValue":
        return node.get("date")
    if typename == "ProjectV2ItemFieldNumberValue":
        return node.get("number")
    if typename == "ProjectV2ItemFieldUserValue":
        return _node_logins(node.get("users"))
    if typename == "ProjectV2ItemFieldMilestoneValue":
        milestone = node.get("milestone")
        return milestone.get("title") if isinstance(milestone, dict) else None
    if typename == "ProjectV2ItemFieldRepositoryValue":
        return _repository_name(node.get("repository"))
    return None


def _activity_from_content(
    content_type: str, content: dict[str, Any]
) -> list[dict[str, Any]]:
    activity: list[dict[str, Any]] = []
    for event_type, field_name in (
        ("created", "createdAt"),
        ("updated", "updatedAt"),
        ("closed", "closedAt"),
        ("merged", "mergedAt"),
    ):
        timestamp = content.get(field_name)
        if timestamp:
            activity.append(
                {
                    "type": event_type,
                    "actor": _login(content.get("author")),
                    "created_at": timestamp,
                    "source": content_type,
                }
            )
    return activity


def _normalize_reviews(content: dict[str, Any]) -> list[dict[str, Any]]:
    reviews = content.get("reviews")
    if not isinstance(reviews, dict):
        return []
    return [
        {
            "author": _login(node.get("author")),
            "state": node.get("state"),
            "submitted_at": node.get("submittedAt"),
        }
        for node in reviews.get("nodes", [])
    ]


def _normalize_commits(content: dict[str, Any]) -> list[dict[str, Any]]:
    commits = content.get("commits")
    if not isinstance(commits, dict):
        return []
    normalized: list[dict[str, Any]] = []
    for node in commits.get("nodes", []):
        commit = node.get("commit")
        if not isinstance(commit, dict):
            continue
        author = commit.get("author")
        user = author.get("user") if isinstance(author, dict) else None
        normalized.append(
            {
                "sha": commit.get("oid"),
                "author": _login(user)
                or (author.get("name") if isinstance(author, dict) else None),
                "authored_at": commit.get("authoredDate"),
            }
        )
    return normalized


def _node_logins(connection: Any) -> list[str]:
    if not isinstance(connection, dict):
        return []
    return [
        node["login"]
        for node in connection.get("nodes", [])
        if isinstance(node, dict) and node.get("login")
    ]


def _label_names(connection: Any) -> list[str]:
    if not isinstance(connection, dict):
        return []
    return [
        node["name"]
        for node in connection.get("nodes", [])
        if isinstance(node, dict) and node.get("name")
    ]


def _login(actor: Any) -> str | None:
    return actor.get("login") if isinstance(actor, dict) else None


def _repository_name(repository: Any) -> str | None:
    return repository.get("nameWithOwner") if isinstance(repository, dict) else None


def parse_args(argv: list[str] | None = None) -> FetchArgs:
    parser = argparse.ArgumentParser(
        description="Fetch read-only GitHub Projects v2 activity as raw report JSON."
    )
    parser.add_argument(
        "--owner", required=True, help="GitHub organization or user login."
    )
    parser.add_argument("--project-number", required=True, type=int)
    parser.add_argument("--start", required=True, help="Report period start date.")
    parser.add_argument("--end", required=True, help="Report period end date.")
    parsed = parser.parse_args(argv)
    return FetchArgs(
        owner=parsed.owner,
        project_number=parsed.project_number,
        start=parsed.start,
        end=parsed.end,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        payload = fetch_project_activity(parse_args(argv))
    except FetchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
