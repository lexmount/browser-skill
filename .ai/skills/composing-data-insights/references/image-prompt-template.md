# Image Prompt Template

For `image` and `image+html` modes. The skill produces the prompt; rendering is **always** delegated to the bundled `scripts/generate_image.py`. This file does not contain `curl`, does not reference gateway URLs, and does not base64-decode anything.

## Principles

- Image generation is for **polished visual summaries and infographics**, not for exact chart rendering.
- Extract every metric, label, date, insight, and risk from the data **first**, then assemble the prompt. Never let the model invent.
- **Keep the prompt tight (~30 lines / ~500 tokens).** Smoke (round 2) found that long prompts (~50+ lines, every section spelled out with rules + layout + required-field labels) trip the upstream provider with HTTP 400 / `data:null`, while the same content trimmed to title + 5 KPIs + 3 risks + 3 recommendations + a single "do not invent" rule succeeds first try.
- Output language follows the data and the user's chat. State the language inline in the prompt rather than as a separate field block.
- Default size: `1024x1024`. For landscape executive briefs, use `1536x1024`. For vertical posters, use `1024x1536`. Confirm size support with the gateway before non-default sizes.

## Prompt Scaffold (compact)

This is the shape that survives the upstream provider. Fill placeholders from the analysis; do not ship `{{...}}` literals.

```text
Create a clean executive-style {{language}} business infographic. Modern dashboard look, presentation-ready, no decorative clutter.

Title: {{title}}

Metrics ({{kpi_count}} KPI cards, exact values):
{{metrics}}

Main visual: {{main_visual_description_one_line}}

Risks section (with severity colors):
{{risks_compact}}

Recommendations: {{recommendations_compact}}

Use only the values above. Do not invent numbers, dates, or labels.
```

Where:

- `{{language}}` — derived from the data / chat (e.g. `Chinese`, `English`)
- `{{title}}` — short, action-oriented
- `{{kpi_count}}` — typically 3–5
- `{{metrics}}` — bullet list, one metric per line, with the exact value (and delta where available)
- `{{main_visual_description_one_line}}` — single sentence describing the chart shape (e.g. `side-by-side bars showing MRR still growing vs monthly churn count accelerating sharply`)
- `{{risks_compact}}` — bullet list, `Severity: short label (key evidence)` per line, max 4 items
- `{{recommendations_compact}}` — semicolon-separated short clauses, max 4 items

If the analysis contains more risks / recommendations than fit, **drop the lowest-priority items** rather than expanding the prompt.

## Delegation to scripts/generate_image.py

Once the prompt is finalized, write it to a unique temp file and invoke the bundled CLI. **Never emit `curl` to chat or to any deliverable, never read `OPENAI_BASE_URL` or `OPENAI_API_KEY` directly, never base64-decode.**

```bash
# Use mktemp so concurrent runs don't collide and to avoid /tmp symlink races.
prompt_file=$(mktemp -t composing-prompt.XXXXXX)
trap 'rm -f "$prompt_file"' EXIT INT TERM   # cleanup on success, error, or kill

cat > "$prompt_file" <<'EOF'
<finalized prompt text>
EOF

python3 "<skill-dir>/scripts/generate_image.py" \
  --prompt "$(cat "$prompt_file")" \
  --output "<user-path>.png"
```

`<skill-dir>` is the directory where `SKILL.md` lives (typically `.ai/skills/composing-data-insights` — the script is co-located so the skill is portable as a single copy). Both `--prompt` and `--output` arguments must be quoted; paths with spaces otherwise break the `--output` value.

For non-default sizes, pass `--size 1536x1024` etc. See the script's `--help` for the full flag list and exit codes (0 success, 2 bad input, 3 HTTP, 4 network, 5 bad response).

For `image+html` mode, `<user-path>.png` must share a directory and stem with the HTML so the relative `<img src="./<stem>.png">` resolves.

## Failure Handling

If `scripts/generate_image.py` exits non-zero, surface its stderr verbatim and stop. The script is bundled, so "missing script" is not an expected failure mode in this skill — if it does happen, the skill copy itself is broken and should be reported / re-installed.

For `image+html` mode, when the image step fails after the HTML has already been written, leave the HTML on disk and prepend the failure callout block from `html-report-template.md` so the missing PNG is visible to the reader rather than producing a silently-broken `<img>` tag.

Never hardcode a fallback gateway URL on failure — surface the error, don't paper over it.
