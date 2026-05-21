---
name: github-activity-report
description: Use when the user asks for GitHub daily, weekly, project, repository, team, organization, or personal activity reports based on issues, pull requests, reviews, commits, or GitHub Projects v2.
---

# GitHub Activity Report

## Overview

Generate GitHub activity reports from read-only GitHub data. This skill owns GitHub scope validation, Projects v2 acquisition guidance, normalization, caveats, and report orchestration. It delegates generic analysis and rendering discipline to `composing-data-insights`; do not rebuild a separate report framework here.

## When To Use

Use this skill when the user asks for:

- GitHub daily, weekly, monthly, or historical activity reports
- Project progress, milestone, iteration, or delivery summaries
- Repository, organization, team, or person activity summaries
- Engineering signals from issues, pull requests, reviews, commits, or Projects v2

Do not use this skill for:

- Writing to GitHub Projects, issues, pull requests, or repositories
- Personal performance ranking
- Generic structured data reports with no GitHub source; use `composing-data-insights`

## Required Boundaries

- **Read-only:** collect data with `gh api` / `gh api graphql`; never mutate GitHub state.
- **Projects v2 first:** if a project can define scope, prefer Projects v2 over loose repository scans.
- **Explicit first-version scope:** current local tooling requires a Projects v2 owner and project number. If the user gives only an org, team, repo, or person, ask for the Projects v2 owner and number instead of silently choosing.
- **Check permissions:** Projects v2 requires `read:project`; private repository activity may require repo access.
- **Caveats are mandatory:** redacted items, invisible repositories, missing fields, rate limits, and missing commit stats must appear in Data Coverage / Limitations.
- **Period honesty:** reports must filter timestamped activity, reviews, commits, and derived metrics to the requested date window.
- **Pagination honesty:** first-page-limited nested GitHub data such as assignees, labels, field values, reviews, commits, and Project user fields must either be fully paginated or produce an explicit coverage caveat.
- **People metrics are activity signals:** PRs, reviews, commits, changed files, and lines changed must not be framed as personal performance, ability, or ranking.

## Workflow

1. **Parse request.** Identify scope, date window, report view, and requested output. Default view is management / delivery; switch to engineering only when requested.
2. **Resolve scope.** Confirm the Projects v2 owner and project number. Candidate discovery for org / team / repo / person requests is a later extension, so ask for the explicit project when it is missing.
3. **Check auth.** Run `gh auth status`; for Projects v2, verify or request `read:project`.
4. **Acquire raw data.** Use `scripts/fetch_github_activity.py` for Projects v2 scopes; it calls `gh api graphql` and emits raw JSON plus coverage caveats for first-page-limited nested connections.
5. **Normalize.** Convert raw data with `scripts/normalize_activity.py` into the report model described in `references/report-model.md`; timestamped activity outside the report period is excluded from items, people metrics, and completion metrics.
6. **Render.** Use `scripts/render_report.py` for Markdown / HTML output and apply `composing-data-insights` analysis discipline for facts, interpretation, risks, and recommendations.
7. **Validate.** Run fixture tests before claiming the skill is working. Run live smoke only when the user has suitable GitHub access.

## Output Contract

Every report should include:

- Summary
- Progress / completed work
- Risks and blockers
- People activity signals with the required non-ranking caveat
- Data Coverage / Limitations
- Links back to visible GitHub evidence where available

Markdown and HTML are supported in the first version. Notion and image reports are later renderer extensions.

## Local Tools

- `scripts/fetch_github_activity.py` fetches Projects v2 raw activity JSON with `gh api graphql`.
- `scripts/normalize_activity.py` exposes `normalize_activity(raw: dict) -> dict`.
- `scripts/render_report.py` exposes `render_markdown(model, view)` and `render_html(model, view)`.
- Tests live next to scripts and are fixture-first:
  - `.venv/bin/python -m pytest .ai/skills/github-activity-report/scripts/test_fetch_github_activity.py`
  - `.venv/bin/python -m pytest .ai/skills/github-activity-report/scripts/test_normalize_activity.py`
  - `.venv/bin/python -m pytest .ai/skills/github-activity-report/scripts/test_render_report.py`

## References

- `references/github-projects-v2.md`
- `references/report-model.md`
- `references/report-templates.md`
- `.ai/skills/composing-data-insights/references/analysis-framework.md`

## Common Mistakes

| Mistake | Fix |
|---|---|
| Building a new generic report engine | Reuse `composing-data-insights`; this skill only adds GitHub acquisition and normalization |
| Treating missing commit stats as zero | Add a caveat; missing data is unknown, not zero |
| Ignoring redacted Project items | Keep a redacted item placeholder and include a coverage caveat |
| Ranking people by activity count | State activity signals only; no performance inference |
| Skipping project confirmation | Ask when multiple candidate Projects v2 match the request |
