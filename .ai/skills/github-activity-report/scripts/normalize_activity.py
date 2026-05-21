"""Normalize GitHub Projects v2 activity into a stable report model."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any


def normalize_activity(raw: dict[str, Any]) -> dict[str, Any]:
    """Return a stable report model from a GitHub raw activity payload."""
    if "scope" not in raw:
        raise ValueError("raw GitHub activity payload must include scope")
    if "period" not in raw:
        raise ValueError("raw GitHub activity payload must include period")

    caveats: list[str] = []
    items: list[dict[str, Any]] = []
    people: dict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    metrics: defaultdict[str, int] = defaultdict(int)
    period = raw["period"]
    period_window = _parse_period(period)

    for raw_item in raw.get("items", []):
        item = _normalize_item(raw_item, caveats, people, metrics, period_window)
        if item is not None:
            items.append(item)

    metrics["total_items"] = len(items)

    return {
        "period": raw["period"],
        "scope": raw["scope"],
        "projects": raw.get("projects", []),
        "items": items,
        "people": {name: dict(values) for name, values in sorted(people.items())},
        "metrics": dict(metrics),
        "caveats": caveats,
    }


def _normalize_item(
    raw_item: dict[str, Any],
    caveats: list[str],
    people: dict[str, defaultdict[str, int]],
    metrics: defaultdict[str, int],
    period_window: tuple[date, date],
) -> dict[str, Any] | None:
    content = raw_item.get("content") or {}
    content_type = str(content.get("type", "Unknown"))
    normalized_type = _normalize_type(content_type)

    caveats.extend(str(caveat) for caveat in raw_item.get("coverage_caveats", []))

    if normalized_type == "redacted":
        caveats.append(
            f"redacted project item {raw_item.get('id', '<unknown>')} was not visible"
        )
        return {
            "id": raw_item.get("id"),
            "type": "redacted",
            "title": "REDACTED",
            "url": None,
            "repository": None,
            "state": "REDACTED",
            "fields": {},
            "activity": [],
        }

    fields = _normalize_fields(
        raw_item.get("field_values", []),
        raw_item.get("id"),
        caveats,
    )
    activity = _filter_by_period(
        raw_item.get("activity", []),
        "created_at",
        period_window,
        caveats,
        "activity",
        raw_item.get("id"),
    )
    reviews = _filter_by_period(
        raw_item.get("reviews", []),
        "submitted_at",
        period_window,
        caveats,
        "reviews",
        raw_item.get("id"),
    )
    commits = _filter_by_period(
        raw_item.get("commits", []),
        "authored_at",
        period_window,
        caveats,
        "commits",
        raw_item.get("id"),
    )
    if _has_timed_entries(raw_item) and not activity and not reviews and not commits:
        caveats.append(
            f"item {raw_item.get('id', '<unknown>')} outside report period was excluded"
        )
        return None

    state = content.get("state")
    title = content.get("title") or "<untitled>"
    actor = content.get("author")
    stats = _normalize_stats(content.get("stats"))
    completed_in_period = _completed_in_period(raw_item, activity, state, fields)

    if normalized_type == "issue":
        metrics["issues"] += 1
    elif normalized_type == "pull_request":
        metrics["pull_requests"] += 1
        for metric in ("additions", "deletions", "changed_files"):
            if metric in stats:
                metrics[metric] += stats[metric]
        if actor:
            people[str(actor)]["pull_requests"] += 1
    elif normalized_type == "draft_issue":
        metrics["draft_issues"] += 1
        if not activity:
            caveats.append(
                f"Draft issue {raw_item.get('id', title)} has no repository-backed activity"
            )

    if completed_in_period:
        metrics["closed_items"] += 1
        for assignee in content.get("assignees", []):
            people[str(assignee)]["closed_items"] += 1

    for review in reviews:
        author = review.get("author")
        if author:
            people[str(author)]["reviews"] += 1

    for commit in commits:
        author = commit.get("author")
        if author:
            people[str(author)]["commits"] += 1
        if "additions" not in commit or "deletions" not in commit:
            caveats.append(
                "commit stats unavailable for "
                f"{commit.get('sha', '<unknown sha>')}; not counted as zero"
            )

    item = {
        "id": raw_item.get("id"),
        "type": normalized_type,
        "title": title,
        "url": content.get("url"),
        "repository": content.get("repository"),
        "state": state,
        "assignees": content.get("assignees", []),
        "labels": content.get("labels", []),
        "fields": fields,
        "activity": activity,
        "completed_in_period": completed_in_period,
    }
    if stats:
        item["stats"] = stats
    return item


def _normalize_type(content_type: str) -> str:
    mapping = {
        "Issue": "issue",
        "PullRequest": "pull_request",
        "DraftIssue": "draft_issue",
        "REDACTED": "redacted",
    }
    return mapping.get(content_type, content_type.lower())


def _normalize_fields(
    field_values: list[dict[str, Any]],
    item_id: str | None,
    caveats: list[str],
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for field_value in field_values:
        field = str(field_value.get("field"))
        value = field_value.get("value")
        if field in fields and fields[field] != value:
            caveats.append(
                f"field conflict on {field} for item {item_id}: {fields[field]} vs {value}"
            )
            continue
        fields[field] = value
    return fields


def _filter_by_period(
    entries: list[dict[str, Any]],
    timestamp_key: str,
    period_window: tuple[date, date],
    caveats: list[str],
    label: str,
    item_id: Any,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    excluded = 0
    for entry in entries:
        timestamp = entry.get(timestamp_key)
        entry_date = _entry_date(timestamp, caveats, label, item_id)
        if entry_date is not None and _is_in_period(entry_date, period_window):
            filtered.append(entry)
        else:
            excluded += 1
    if excluded:
        caveats.append(
            f"{label} outside report period for item {item_id} were excluded"
        )
    return filtered


def _parse_period(period: Any) -> tuple[date, date]:
    if not isinstance(period, dict):
        raise ValueError("raw GitHub activity payload period must be an object")
    start = _parse_period_date(period.get("start"), "period.start")
    end = _parse_period_date(period.get("end"), "period.end")
    if start > end:
        raise ValueError("period.start must be on or before period.end")
    return start, end


def _parse_period_date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be YYYY-MM-DD") from exc


def _entry_date(
    value: Any,
    caveats: list[str],
    label: str,
    item_id: Any,
) -> date | None:
    date_key = _date_key(value)
    if date_key is None:
        return None
    try:
        return date.fromisoformat(date_key)
    except ValueError:
        caveats.append(f"invalid {label} timestamp for item {item_id}: {value}")
        return None


def _is_in_period(value: date, period_window: tuple[date, date]) -> bool:
    start, end = period_window
    return start <= value <= end


def _date_key(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    return value[:10]


def _normalize_stats(stats: Any) -> dict[str, int]:
    if not isinstance(stats, dict):
        return {}
    return {
        key: value
        for key, value in stats.items()
        if key in {"additions", "deletions", "changed_files"} and isinstance(value, int)
    }


def _has_timed_entries(raw_item: dict[str, Any]) -> bool:
    return (
        _has_timestamp(raw_item.get("activity", []), "created_at")
        or _has_timestamp(raw_item.get("reviews", []), "submitted_at")
        or _has_timestamp(raw_item.get("commits", []), "authored_at")
    )


def _has_timestamp(entries: list[dict[str, Any]], timestamp_key: str) -> bool:
    return any(_date_key(entry.get(timestamp_key)) is not None for entry in entries)


def _completed_in_period(
    raw_item: dict[str, Any],
    activity: list[dict[str, Any]],
    state: Any,
    fields: dict[str, Any],
) -> bool:
    is_completed = (
        str(state).upper() in {"CLOSED", "MERGED", "DONE"}
        or fields.get("Status") == "Done"
    )
    if not is_completed:
        return False
    if not _has_timestamp(raw_item.get("activity", []), "created_at"):
        return True
    return any(event.get("type") in {"closed", "merged"} for event in activity)
