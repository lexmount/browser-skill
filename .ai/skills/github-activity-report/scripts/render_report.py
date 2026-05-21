"""Render GitHub activity report models to Markdown or self-contained HTML."""

from __future__ import annotations

from html import escape
import re
from typing import Any


def render_markdown(model: dict[str, Any], view: str = "management") -> str:
    """Render a report model as Markdown."""
    period = _period_label(model)
    lines = [
        "# GitHub Activity Report",
        "",
        f"**Period:** {period}",
        f"**Scope:** {_scope_label(model.get('scope', {}))}",
        f"**View:** {view}",
        "",
        "## Summary",
        "",
        f"- Total tracked items: {model.get('metrics', {}).get('total_items', 0)}",
        f"- Completed or merged items: {model.get('metrics', {}).get('closed_items', 0)}",
        f"- Pull requests: {model.get('metrics', {}).get('pull_requests', 0)}",
        "",
        "## Completed Work",
        "",
    ]
    completed = [
        item
        for item in model.get("items", [])
        if item.get("completed_in_period")
        or (
            "completed_in_period" not in item
            and (
                str(item.get("state")).upper() in {"CLOSED", "MERGED"}
                or item.get("fields", {}).get("Status") == "Done"
            )
        )
    ]
    if completed:
        for item in completed:
            lines.append(f"- {_item_label(item)}")
    else:
        lines.append("- No completed work was visible in the provided data.")

    lines.extend(
        [
            "",
            "## Risks",
            "",
        ]
    )
    caveats = model.get("caveats", [])
    if caveats:
        lines.append("- Coverage caveats may affect trend interpretation.")
    else:
        lines.append("- No data coverage caveats were reported.")

    lines.extend(
        [
            "",
            "## People Activity Signals",
            "",
            "These are activity signals, not a performance ranking.",
            "",
        ]
    )
    people = model.get("people", {})
    if people:
        for name, stats in sorted(people.items()):
            parts = [f"{metric}: {value}" for metric, value in sorted(stats.items())]
            lines.append(f"- {name}: {', '.join(parts)}")
    else:
        lines.append("- No person-level activity was visible in the provided data.")

    if view == "engineering":
        lines.extend(
            [
                "",
                "## Engineering Signals",
                "",
                "- Review, PR, and commit activity should be read with repository and coverage context.",
            ]
        )

    lines.extend(["", "## Data Coverage / Limitations", ""])
    if caveats:
        lines.extend(f"- {caveat}" for caveat in caveats)
    else:
        lines.append("- No limitations reported.")

    return "\n".join(lines) + "\n"


def render_html(model: dict[str, Any], view: str = "management") -> str:
    """Render a report model as self-contained HTML."""
    markdown = render_markdown(model, view=view)
    body = _wrap_lists(
        "\n".join(_markdown_line_to_html(line) for line in markdown.splitlines())
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GitHub Activity Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #172033; }}
    main {{ max-width: 960px; margin: 0 auto; }}
    h1, h2 {{ color: #0f172a; }}
    li {{ margin: 6px 0; }}
    code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def _markdown_line_to_html(line: str) -> str:
    if line.startswith("# "):
        return f"<h1>{escape(line[2:])}</h1>"
    if line.startswith("## "):
        return f"<h2>{escape(line[3:])}</h2>"
    if line.startswith("- "):
        return f"<li>{_markdown_inline_to_html(line[2:])}</li>"
    if not line:
        return ""
    return f"<p>{escape(line)}</p>"


def _markdown_inline_to_html(text: str) -> str:
    match = re.fullmatch(r"\[(.+)]\((https?://[^)]+)\)", text)
    if match is None:
        return escape(text)
    label, url = match.groups()
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def _wrap_lists(body: str) -> str:
    output: list[str] = []
    in_list = False
    for line in body.splitlines():
        is_li = line.startswith("<li>")
        if is_li and not in_list:
            output.append("<ul>")
            in_list = True
        elif not is_li and in_list:
            output.append("</ul>")
            in_list = False
        output.append(line)
    if in_list:
        output.append("</ul>")
    return "\n".join(output)


def _period_label(model: dict[str, Any]) -> str:
    period = model.get("period", {})
    start = period.get("start", "unknown")
    end = period.get("end", "unknown")
    return f"{start} to {end}"


def _scope_label(scope: dict[str, Any]) -> str:
    parts = [str(value) for value in scope.values() if value]
    return " / ".join(parts) if parts else "unspecified"


def _item_label(item: dict[str, Any]) -> str:
    title = item.get("title", "<untitled>")
    state = item.get("state") or item.get("fields", {}).get("Status") or "unknown"
    url = item.get("url")
    if url:
        return f"[{title} ({state})]({url})"
    return f"{title} ({state})"
