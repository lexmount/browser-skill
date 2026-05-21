# GitHub Projects v2 Reference

## Access

- Use `gh auth status` to verify authentication.
- Projects v2 reads require `read:project`.
- Private repository issue, pull request, review, and commit activity may require repository access in addition to project access.

## Query Shape

Use GraphQL through `gh api graphql`.

Primary concepts:

- `ProjectV2Owner`: organization or user that owns projects.
- `ProjectV2`: project metadata, fields, and items.
- `ProjectV2Item`: project item wrapper.
- Item content can be `Issue`, `PullRequest`, `DraftIssue`, or `REDACTED`.
- Field values are heterogeneous; normalize by field name and keep conflicts as caveats.

## Scope Resolution

When the request gives only an org, team, repo, or person:

1. Search visible Projects v2 under the likely owner.
2. Prefer projects whose title, linked repository, or visible items match the request.
3. If multiple candidates remain, present a short candidate list and ask the user to choose.

Do not silently pick one project when the match is ambiguous.

## Coverage Caveats

Include caveats for:

- `REDACTED` items.
- Draft issues without repository-backed activity.
- Field name conflicts or missing expected fields.
- Private repositories that are not visible.
- Rate limits or partial GraphQL failures.
- Commit stats that are unavailable.

## Source Links

- GitHub GraphQL `ProjectV2`: https://docs.github.com/en/graphql/reference/objects#projectv2
- GitHub GraphQL `ProjectV2Item`: https://docs.github.com/en/graphql/reference/objects#projectv2item
- GitHub GraphQL `ProjectV2Owner`: https://docs.github.com/en/graphql/reference/interfaces#projectv2owner
- GitHub OAuth scopes: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps#available-scopes
- GitHub CLI `gh api`: https://cli.github.com/manual/gh_api
