# GitHub Activity Report Model

The normalized model is a JSON-serializable dictionary with stable top-level keys.

```json
{
  "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "scope": {"owner": "org-or-user", "project": "optional", "repository": "optional", "person": "optional"},
  "projects": [],
  "items": [],
  "people": {},
  "metrics": {},
  "caveats": []
}
```

## Items

Each item should include:

- `id`
- `type`: `issue`, `pull_request`, `draft_issue`, `redacted`, or a lower-case fallback
- `title`
- `url`
- `repository`
- `state`
- `assignees`
- `labels`
- `fields`
- `activity`
- `completed_in_period`
- `stats` when PR-level additions, deletions, or changed files are available

`redacted` items keep a placeholder item and a caveat. Do not drop them.

Timestamped activity, reviews, and commits are filtered to the inclusive report
period before the model is rendered. Items with timestamped evidence entirely
outside the period are excluded from the normalized item list and derived
metrics.

## People

People metrics are activity signals only. Valid examples:

- `closed_items`
- `pull_requests`
- `reviews`
- `commits`

Do not add derived performance ratings or rankings.

## Metrics

Metrics can include:

- `total_items`
- `closed_items`
- `issues`
- `pull_requests`
- `draft_issues`
- `additions`
- `deletions`
- `changed_files`

Unknown values stay absent and must not be converted to zero.

## Caveats

Every partial or ambiguous condition belongs in `caveats`, including redactions, inaccessible repositories, missing commit stats, invalid timestamps, draft issue limitations, Project field conflicts, first-page-limited nested GitHub connections, and activity excluded because it is outside the report period.
