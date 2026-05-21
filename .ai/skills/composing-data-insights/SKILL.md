---
name: composing-data-insights
description: Use when the user provides structured or semi-structured data (CSV, Excel, JSON, pasted tables, or metric snippets) and asks for a polished executive-style deliverable — an HTML report, an infographic image, or both.
---

# Composing Data Insights

## Overview

Turn user-supplied data into a polished deliverable for executive review. Three caller-selectable rendering modes:

- `html` — a single self-contained `.html` file (inline CSS / inline SVG, no CDN by default)
- `image` — one or more PNG executive infographic images, produced by invoking the bundled `scripts/generate_image.py`
- `image+html` — HTML plus one or more PNG images, written to the same directory and sharing a stem; the HTML references the PNG files via relative `<img>` tags (never base64 inline)

The four-bucket analysis (facts / interpretation / risks / recommendations) is computed in every mode — it is upstream of both the HTML body and the image prompt, never a standalone deliverable.

### Operating constraints (always)

- **No data fetching.** Skill never queries databases, APIs, or scrapes — the user supplies the bytes.
- **No re-implementing image I/O.** Image generation always goes through the bundled `scripts/generate_image.py`; never emit `curl`, never base64-decode in chat, never hardcode a gateway URL.
- **Language-neutral.** Output language follows the data and the user's chat — nothing is hardcoded to any specific language.
- **PII / secrets aware.** Sensitive fields are detected, confirmed with the user, and aggregated / masked / excluded before they reach the HTML body or the image prompt. See `references/pii-and-secrets.md`.

## When to Use

Use this skill when the user:

- Pastes / attaches data (CSV, Excel, JSON, table, metric snippet) and wants a deliverable for review
- Provides, or another skill hands off, a normalized report model that needs facts / interpretation / risks / recommendations and polished Markdown / HTML / image output
- Asks for a "report", "dashboard", "infographic", "executive summary", or similar polished artifact
- Wants a written analysis with insights, hidden risks, and recommendations

Do **not** use this skill when:

- The user is asking for a live SQL pull, API fetch, or scrape — that's data-acquisition, out of scope here
- The user wants "just an image" of something unrelated to data (e.g. "draw a cyberpunk city") — use a separate general image capability outside this skill if the host has one
- The user asks for a single number to format / a quick arithmetic result — too small, just answer in chat
- The user wants a multi-page paginated report or interactive dashboard — out of scope

## Mode Contract

The caller picks one of `image` / `html` / `image+html`. The caller may also specify `image_count` from 1 to 3. The skill must not silently choose mode. If mode is unspecified, ask once before rendering:

> Which mode would you like — `image` (PNG infographic image[s]), `html` (self-contained report), or `image+html` (HTML plus PNG image[s] in the same directory)?

For `image+html`:

- Files share a stem from the user-provided output path (e.g. `/tmp/q1-review` → `q1-review.html` + `q1-review.png`, or `q1-review-1.png` ... `q1-review-3.png` when `image_count > 1`)
- Files land in the same directory
- The HTML references PNG files via relative `<img>` tags — never base64 inline
- Render the HTML first; invoke the bundled `scripts/generate_image.py` second; if the image step fails, the HTML is still on disk and the missing PNG is flagged at the top of the report

## Default Workflow

For every mode, follow these steps:

1. **Understand the data.** Identify metrics, dimensions, time periods, units, segments, and business context. If the input is an upstream report model, preserve its scope, period, caveats, and evidence links instead of flattening them away. State what's clear and what's ambiguous.
2. **Sensitivity check.** Scan for PII / secrets — emails, phone numbers, person names, customer / company names, API tokens, passwords, secret-like strings, internal IDs that look like credentials. If any are present, confirm with the user before proceeding and aggregate / mask / exclude before any field enters the HTML body or the image prompt. Use `references/pii-and-secrets.md` for the detection list and the masking rules.
3. **Quality-check.** Use `references/risk-and-pattern-checks.md` to flag missing values, duplicates, inconsistent labels, suspicious zeros, outliers, small sample sizes, unclear definitions, mixed units. Mention quality issues explicitly — never silently clean or ignore.
4. **Extract insights.** Use `references/analysis-framework.md` to organize facts, interpretation, risks, and recommendations. Find trends, drivers, segment differences, conversion bottlenecks, anomalies, non-obvious patterns.
5. **Surface risks.** Include risks even when the headline trend is positive. Each risk gets: name, severity (High / Medium / Low), evidence from the data, why it matters, suggested action.
6. **Render per mode:**
   - `html` — write self-contained `.html` using `references/html-report-template.md` as a starting point. Adapt to data; do not ship placeholder text verbatim.
   - `image` — finalize prompt using `references/image-prompt-template.md`, then invoke the bundled `scripts/generate_image.py` (see Hand-off below). Do not emit `curl` snippets.
   - `image+html` — produce the HTML first with the relative `<img>` reference; then invoke `scripts/generate_image.py` to materialize the PNG to the same directory and stem.

## Hand-off to scripts/generate_image.py

When the mode includes an image, the rendering goes through the **bundled** `scripts/generate_image.py`. This skill never re-implements the HTTP call.

Invocation pattern (run by the agent, not embedded in the deliverable):

```bash
# Use mktemp so concurrent runs don't collide and to avoid /tmp symlink races.
prompt_file=$(mktemp -t composing-prompt.XXXXXX)
trap 'rm -f "$prompt_file"' EXIT INT TERM   # cleanup on success, error, or kill

cat > "$prompt_file" <<'EOF'
<finalized prompt text — see references/image-prompt-template.md>
EOF

python3 "<skill-dir>/scripts/generate_image.py" \
  --prompt "$(cat "$prompt_file")" \
  --output "<user-path>.png"
```

When `image_count > 1`, pass `--n <image_count>` and let the bundled script expand the output paths to `<stem>-1.png`, `<stem>-2.png`, and so on. Keep `image_count` bounded to 3 for report / slide-style deliverables unless the caller explicitly justifies more.

`<skill-dir>` is the directory where this `SKILL.md` lives (typically `.ai/skills/composing-data-insights` in this repo, but the bundled script is co-located so the skill is portable as a single copy). `<user-path>.png` must be quoted — paths with spaces (common on macOS / Windows-mounted shares) otherwise break the `--output` argument.

Rules:

- Never emit `curl` to chat or to any deliverable
- Never read `OPENAI_BASE_URL` or `OPENAI_API_KEY` directly — `generate_image.py` does that
- Never base64-decode or pipe `jq | base64 --decode` — fragile, already handled inside the script
- Never use a fixed temp file path like `/tmp/composing-prompt.txt` — concurrent runs will collide; use `mktemp`
- Always pair `mktemp` with `trap 'rm -f "$prompt_file"' EXIT INT TERM` so the file is removed on success, error, or kill (`pii-and-secrets.md` requires cleanup on success or failure)
- Always quote `--prompt` and `--output` arguments

If the user's environment is missing `OPENAI_API_KEY`, `generate_image.py` exits with code 2 and prints a one-line reason to stderr — surface that verbatim and stop. Do **not** hardcode a fallback gateway URL.

## Upstream Report Model Handoff

Other skills may pass a normalized report model instead of raw tabular data. Treat that model as the structured input and keep these fields intact when present:

- `period`
- `scope`
- `metrics`
- `items`
- `people`
- `caveats`
- source URLs or evidence links

For GitHub reports, `github-activity-report` owns acquisition and normalization. This skill owns the generic analysis discipline and presentation layer. Do not fetch GitHub data from this skill.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Inventing numbers / dates / categories | Output contains values not in the data | Re-derive every figure from the data; if missing, say so |
| Conflating fact and interpretation | Risks read like opinions, not evidence | Use the four-bucket framework in `references/analysis-framework.md` strictly |
| Embedding base64 PNGs in HTML | HTML grows past 1 MB; image not regeneratable in isolation | Use `<img src="./<stem>.png">` always |
| Hardcoding output language | Output is always one language regardless of data / chat | Pick language from the data and the user's chat |
| Switching mode silently | User asked `html`, got an image | Ask once if mode is unclear; never default |
| Ignoring requested image count | User asked for 3 report images, got 1 PNG | Pass `--n <image_count>` to the bundled script and reference every PNG in HTML |
| Re-emitting curl for image generation | Two paths doing the same I/O | Always invoke the bundled `scripts/generate_image.py` |
| Producing the runbook instead of running it | Skill output is "here's how to do it" instead of the actual report | The skill produces the report; invoke `scripts/generate_image.py` for the image |
| Hardcoded `/tmp/composing-prompt.txt` | Concurrent runs collide; symlink race on shared hosts | Use `mktemp -t composing-prompt.XXXXXX` + `trap 'rm -f "$prompt_file"' EXIT INT TERM` so cleanup happens on success, error, or kill |
| Unquoted `--output` path | Path with spaces (macOS / Windows shares) breaks the argument | Always `--output "<user-path>.png"` |
| Sensitive fields leak to image prompt | Raw emails / names / tokens end up in the rendered PNG | Run sensitivity check (Step 2) before any field enters the prompt; see `references/pii-and-secrets.md` |

## Smoke

End-to-end smoke runbook + toy fixture live at `smoke/README.md` and `smoke/toy-saas.csv`. Use them to verify all three modes after edits. Image and image+html modes hit the real gateway; html mode is offline.
