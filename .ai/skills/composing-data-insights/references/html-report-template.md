# HTML Report Template

Reference template for the `html` and `image+html` modes. **Starting point, not a contract.** Adapt to the data; do not ship placeholder text verbatim.

## Usage Rules

- Inline CSS only. No CDN by default.
- Chart.js / ECharts allowed only when the caller explicitly opts in to interactive charts.
- For static charts, prefer **inline SVG**, **CSS bars**, or **HTML tables**.
- **Language follows the data and the user's chat.** Do not hardcode `<html lang="zh-CN">` or fixed section titles like `核心洞察` / `Key Insights` — the agent fills `{{lang}}` and the section heading placeholders based on context.
- For `image+html` mode: include the image via `<img src="./{{image_relative_path}}">` — relative path, never base64 inline. The image file lives in the same directory as the HTML and shares the stem.
- The "do not over-design" rule applies: prioritize readability and factual accuracy. Cards, KPI grids, and tables before decoration.

## Required Sections

Every report must contain these — the headings are language-neutral placeholders that the agent fills:

1. Title + short subtitle
2. Executive summary
3. KPI cards (3–5)
4. Main insights (Interpretation bucket)
5. Hidden risks (each with severity + evidence + why-it-matters + suggested-action)
6. Visual analysis (charts, where helpful)
7. Recommendations
8. Data quality notes

## Severity Border Convention

Use these CSS classes on risk callout cards:

| Class | When |
|---|---|
| `.risk-high` | Severity = High |
| `.risk-medium` | Severity = Medium |
| `.risk-low` | Severity = Low |

The exact colors are agent-pickable (default suggestion: red / amber / green). Do not lock to a brand palette unless the user provides one.

## Minimal Template

```html
<!doctype html>
<html lang="{{lang}}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{report_title}}</title>
  <style>
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f6f7f9; color: #111827; }
    .page { max-width: 1180px; margin: 0 auto; padding: 32px; }
    .hero { background: #111827; color: white; border-radius: 24px; padding: 32px; margin-bottom: 24px; }
    .hero h1 { margin: 0 0 8px 0; font-size: 28px; }
    .hero p { margin: 0; opacity: 0.85; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
    .card { background: white; border-radius: 18px; padding: 20px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08); }
    .metric { font-size: 32px; font-weight: 700; margin: 8px 0; }
    .metric-label { font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
    .section { margin-top: 24px; }
    .risk-high   { border-left: 5px solid #dc2626; }
    .risk-medium { border-left: 5px solid #f59e0b; }
    .risk-low    { border-left: 5px solid #10b981; }
    .risk h3 { margin: 0 0 4px 0; }
    .risk .meta { font-size: 12px; color: #6b7280; margin-bottom: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
    th { background: #f9fafb; font-weight: 600; }
    .hero-image img { width: 100%; height: auto; border-radius: 18px; display: block; }
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>{{report_title}}</h1>
      <p>{{report_subtitle}}</p>
    </section>

    {{#if image_relative_path}}
    <section class="section hero-image">
      <img src="./{{image_relative_path}}" alt="{{report_title}}" />
    </section>
    {{/if}}

    <section class="section">
      <h2>{{executive_summary_heading}}</h2>
      <div class="card">{{executive_summary_body}}</div>
    </section>

    <section class="section grid">{{kpi_cards}}</section>

    <section class="section card">
      <h2>{{insights_section_heading}}</h2>
      {{insights}}
    </section>

    <section class="section card">
      <h2>{{risks_section_heading}}</h2>
      {{risks}}
    </section>

    <section class="section card">
      <h2>{{visual_analysis_heading}}</h2>
      {{charts}}
    </section>

    <section class="section card">
      <h2>{{recommendations_section_heading}}</h2>
      {{recommendations}}
    </section>

    <section class="section card">
      <h2>{{data_quality_section_heading}}</h2>
      {{data_quality_notes}}
    </section>
  </main>
</body>
</html>
```

## Image Embedding Snippet (image+html mode only)

The `{{#if image_relative_path}}` block above is shown for clarity — in practice, the agent emits the `<section class="hero-image">` block when mode is `image+html` and omits it for `html`-only mode. The block must reference the PNG via a relative path (`./<stem>.png`), never base64.

If image generation fails after the HTML is written, replace the `<img>` with a clearly-flagged placeholder at the **top** of the report:

```html
<section class="section card risk-high">
  <h2>{{image_failed_heading}}</h2>
  <p>{{image_failed_message}}</p>
</section>
```

This makes the failure visible to the reader rather than producing a silently-broken `<img>` tag.

## What Not to Do

- Don't embed PNGs as `data:image/png;base64,...` — kills regeneratability and balloons file size
- Don't hardcode `<html lang="zh-CN">` (or any specific lang) into the template body
- Don't ship `{{report_title}}` as visible placeholder text — fill it from the data first
- Don't add CDN links for fonts / charts unless the caller has opted in
- Don't introduce JavaScript unless interactive charts were explicitly requested
