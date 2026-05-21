# Smoke Runbook

End-to-end checks for the `composing-data-insights` skill. Three modes, one fixture. Image-mode checks hit the live gateway; HTML-mode is offline.

## Fixture

`toy-saas.csv` — 6 monthly rows for a fake SaaS:

| month | mrr_usd | new_customers | churned_customers | active_customers |
|---|---|---|---|---|
| 2025-11 | 120000 | 45 | 8 | 612 |
| 2025-12 | 128500 | 52 | 10 | 654 |
| 2026-01 | 131200 | 48 | 15 | 687 |
| 2026-02 | 134000 | 40 | 18 | 709 |
| 2026-03 | 135500 | 38 | 22 | 725 |
| 2026-04 | 136200 | 35 | 28 | 732 |

The trap: revenue is still inching up, **but** new customers are falling and churn is rising sharply. A correct analysis surfaces "accelerating churn despite headline growth" as a High-severity hidden risk.

## Prerequisites

- `OPENAI_API_KEY` and `OPENAI_BASE_URL` exported (image / image+html modes only)
- Bundled `scripts/generate_image.py` present (it ships with this skill — if missing, the skill copy itself is broken)
- Write access to `/tmp/composing-smoke/`

```bash
mkdir -p /tmp/composing-smoke
```

## Mode 1: html (offline)

**Prompt to operate the skill:**

> Use the composing-data-insights skill on `.ai/skills/composing-data-insights/smoke/toy-saas.csv`. Mode: `html`. Output path: `/tmp/composing-smoke/q1-saas-review.html`.

**Expected:**

- File `/tmp/composing-smoke/q1-saas-review.html` exists, opens in a browser
- Every metric in the CSV is reflected in the report (MRR, new customers, churned customers, active customers, by month)
- Zero invented numbers (no fabricated CAC, LTV, ARR projections, industry benchmarks)
- "Accelerating churn despite revenue growth" appears as a High-severity risk
- No `<html lang="zh-CN">` or other hardcoded language attribute — language matches the chat / data
- No CDN links, no JavaScript

**Verify:**

```bash
test -s /tmp/composing-smoke/q1-saas-review.html && echo "OK: html exists" || echo "FAIL: html missing"
grep -E 'data:image/' /tmp/composing-smoke/q1-saas-review.html && echo "FAIL: base64 image embedded" || echo "OK: no base64 image"
grep -E 'cdn\.|googleapis\.' /tmp/composing-smoke/q1-saas-review.html && echo "FAIL: CDN link" || echo "OK: no CDN"
```

## Mode 2: image (live gateway)

**Prompt to operate the skill:**

> Use the composing-data-insights skill on `.ai/skills/composing-data-insights/smoke/toy-saas.csv`. Mode: `image`. Output path: `/tmp/composing-smoke/q1-saas-review.png`. Size: `1024x1024`.

**Expected:**

- Agent finalizes a polished prompt covering title / metrics / insights / risks / recommendations
- Agent invokes `python3 .ai/skills/composing-data-insights/scripts/generate_image.py --prompt ... --output /tmp/composing-smoke/q1-saas-review.png` (the bundled script — same skill folder)
- File `/tmp/composing-smoke/q1-saas-review.png` is non-empty, valid PNG

**Verify:**

```bash
file /tmp/composing-smoke/q1-saas-review.png | grep -q "PNG image data" && echo "OK: png valid" || echo "FAIL: not a png"
test $(stat -f%z /tmp/composing-smoke/q1-saas-review.png 2>/dev/null || stat -c%s /tmp/composing-smoke/q1-saas-review.png) -gt 100000 && echo "OK: png > 100 KB" || echo "FAIL: png too small"
```

**Gateway flakiness**: round 1 documented that the live gateway returns 400 / `data:null` intermittently (~30% failure rate). If the first attempt fails, retry up to 3 times before declaring blocked. Document the retry count in the plan's Validation section.

## Mode 3: image+html (live gateway)

**Prompt to operate the skill:**

> Use the composing-data-insights skill on `.ai/skills/composing-data-insights/smoke/toy-saas.csv`. Mode: `image+html`. Output stem: `/tmp/composing-smoke/q1-saas-combined`. (This produces `q1-saas-combined.html` and `q1-saas-combined.png` in the same directory.)

**Expected:**

- Both files in `/tmp/composing-smoke/`: `q1-saas-combined.html` and `q1-saas-combined.png`
- HTML contains `<img src="./q1-saas-combined.png">` — relative reference, not base64
- Image renders inside the HTML when opened in a browser

**Verify:**

```bash
test -s /tmp/composing-smoke/q1-saas-combined.html && test -s /tmp/composing-smoke/q1-saas-combined.png && echo "OK: both files exist" || echo "FAIL: one or both missing"
grep -F 'src="./q1-saas-combined.png"' /tmp/composing-smoke/q1-saas-combined.html && echo "OK: relative img reference" || echo "FAIL: img reference missing or wrong"
grep -E 'data:image/' /tmp/composing-smoke/q1-saas-combined.html && echo "FAIL: base64 image inlined" || echo "OK: no base64 inline"
```

## Failure-Mode Hints

- **Gateway returns 400 / data:null** (round 1 known issue): retry up to 3 times
- **Agent emits `curl` to chat**: skill-bug — re-read the Hand-off section of `SKILL.md` and `image-prompt-template.md` Delegation block
- **HTML contains base64 image**: skill-bug — re-read `html-report-template.md` "What Not to Do"
- **Output language is wrong** (e.g. fixed Chinese when chat is English): skill-bug — re-read the "Language" notes in both templates
- **Numbers in report don't match CSV**: skill-bug or model failure — re-read `analysis-framework.md` "Never-Invent Rule"
