# Risk and Pattern Checks

Three checklists to run on every dataset, plus the severity convention used everywhere this skill emits a risk.

## 1. Data Quality Risks

Mention these explicitly when present. Never silently clean or ignore.

- **Missing values** — null / empty / `N/A` cells; how many rows / which columns
- **Duplicate rows** — exact duplicates or near-duplicates by primary key
- **Inconsistent labels** — same concept spelled differently (`US`, `USA`, `United States`)
- **Inconsistent date formats** — `2026-04`, `Apr 2026`, `4/26` mixed in one column
- **Suspicious zeros / nulls** — a metric that's never zero in reality showing zero in some rows
- **Impossible values** — negative counts, percentages > 100, dates in the future
- **Extreme outliers** — values > 3σ from the mean, or 10x typical row
- **Small sample** — fewer than ~10 rows for trend analysis, fewer than ~30 for segment comparison
- **Unclear metric definitions** — what does "active customer" mean? what's the denominator of the conversion rate?
- **Mixed units / currencies** — USD + CNY + EUR in one revenue column without a currency field

## 2. Business Risks

Look for these even when the headline trend is positive.

- **Concentration** — top 1 customer / region / channel / product accounts for >30% of revenue
- **Cost-vs-revenue** — costs growing faster than revenue
- **Traffic-vs-conversion** — user / traffic growth without proportional conversion growth
- **Rising acquisition cost** — CAC trending up while LTV flat or down
- **Falling conversion / retention** — funnel rates or cohort retention dropping
- **Segment variance** — wide gap between best and worst segment, with the worst growing faster as a share
- **Hidden subgroup weakness** — aggregate looks fine but a key subgroup (top tier, biggest market, longest cohort) is declining
- **Headline driven by one factor** — total growth attributable to a single product launch / one-time event / large customer
- **Declining quality behind volume** — order count up but average value or NPS down
- **Unsustainable growth pattern** — exponential metric that requires equally exponential inputs (capacity, hiring, spend)

## 3. Non-Obvious Patterns

Actively check for these — they don't surface unless you look.

- **Sudden drops or spikes** — single-period anomalies; investigate before averaging them away
- **Trend reversals** — direction change in the most recent 1–2 periods
- **Flat revenue despite volume growth** — pricing erosion or downmix
- **Average values hiding segment-level decline** — Simpson's paradox risk
- **Cohort vs aggregate divergence** — recent cohorts behaving differently than older ones, masked by aggregate metrics
- **Top-N domination** — a few rows / customers / products driving the result, fragile
- **Weak denominator / small-n effects** — high percentages computed on tiny denominators

## Severity Convention

Every risk gets exactly one severity label. Use these definitions:

| Level | When to use |
|---|---|
| **High** | Likely material business impact; clear evidence in the data; urgent action recommended |
| **Medium** | Meaningful risk; partial evidence; needs follow-up validation or monitoring |
| **Low** | Minor issue; weak signal; mostly a monitoring point or data-hygiene reminder |

Required fields for every risk (whether emitted in chat, HTML, or image prompt):

- **Name** — short label (e.g. "Accelerating churn despite revenue growth")
- **Severity** — High / Medium / Low
- **Evidence** — pointer to specific rows or values from the data
- **Why it matters** — business consequence in one sentence
- **Suggested action** — concrete next step

If you can't fill all five, the item isn't a risk yet — it's a hypothesis. Keep it for the analyst to investigate; do not promote it to a deliverable.
