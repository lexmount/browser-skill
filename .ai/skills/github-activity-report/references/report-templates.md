# GitHub Report Templates

## Management / Delivery View

Use this by default.

Sections:

1. Summary
2. Progress
3. Completed Work
4. Risks / Blockers
5. People Activity Signals
6. Data Coverage / Limitations

Tone:

- Concise and evidence-based.
- Emphasize delivery state, risk, and next action.
- Do not rank individuals.

## Engineering Signals View

Use only when the user asks for engineering effectiveness, review flow, throughput, or similar signals.

Additional signals:

- PR review activity.
- Merge / close activity.
- Commit activity where stats are available.
- Stale issue / PR indicators when present in source data.

Required caveat:

> People-level counts are activity signals. They are not a performance ranking and should be interpreted with repository ownership, review load, and data coverage context.

## Data Coverage / Limitations

Always include this section. It should mention:

- Date window.
- Projects / repositories included.
- Redacted or inaccessible items.
- Missing fields or commit stats.
- Scope limitations requested by the user.
