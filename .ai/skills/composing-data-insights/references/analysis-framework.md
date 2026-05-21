# Analysis Framework

The four-bucket discipline. Every piece of analysis output goes into exactly one of these. Mixing them is the most common reason an analysis reads as opinion rather than insight.

## Four Buckets

### Facts

Values **directly supported by the provided data**. A fact is a number, a date, a label, a count, or a category that appears in (or is exactly derivable from) the dataset.

- "Revenue grew from $120,000 in November 2025 to $136,200 in April 2026."
- "Churn count rose from 8 (2025-11) to 28 (2026-04)."
- "The dataset has 6 monthly rows; no missing values."

If you can't point to the rows that prove it, it isn't a fact.

### Interpretation

What the facts likely mean. Interpretation depends on context, comparison, or judgement — but it's always anchored to a specific fact above.

- "MRR growth is decelerating — month-over-month gains shrank from $8,500 (Nov→Dec) to $700 (Mar→Apr)."
- "The customer base is growing more slowly than churn — net adds went from +37 to +7 over the period."

Interpretation should never introduce numbers that aren't in the Facts bucket.

### Risks

What could go wrong, what's hidden, what the headline trend is masking. Each risk has five required fields:

- **Name** — short label
- **Severity** — High / Medium / Low (see `risk-and-pattern-checks.md`)
- **Evidence** — pointer to specific facts
- **Why it matters** — business consequence
- **Suggested action** — concrete next step

Risks are not "possible negatives in general" — they are "specific things this dataset shows."

### Recommendations

Concrete next actions. A recommendation is something the reader can do this week or this quarter, with a defined trigger and a defined outcome.

- "Investigate why churn doubled between January and April — segment by acquisition cohort and pricing tier."
- "Pause expansion ad spend until net adds recover above +15/month."

Vague suggestions ("improve retention") don't count. If you can't say who does what by when, it's not yet a recommendation.

## Never-Invent Rule

Never fabricate:

- Numbers, percentages, rates, ratios
- Dates, time periods, fiscal quarters
- Categories, segments, cohorts
- Labels, product names, customer names
- Benchmarks ("industry average", "best-in-class", "typical SaaS")

If the data is insufficient to support a claim, say what's missing and produce the best partial analysis. "We can't compute LTV without ARPU and gross margin — given only MRR and churn, here's what we can say…" is the right shape.

If the user asks for a benchmark and the data does not contain one, refuse to fabricate. Say: "The dataset has no comparison anchor — would you like to provide a benchmark, or should I describe trends in absolute terms only?"

## Response Shape

When emitting analysis text (in chat, in HTML body, or as a prompt input), prefer this ordering:

1. **Executive summary** (2–3 sentences, the single most important point first)
2. **Key metrics** (3–5 KPI values from the Facts bucket)
3. **Main insights** (3–5 items from the Interpretation bucket)
4. **Hidden risks** (each with the five required fields)
5. **Recommendations** (concrete actions)
6. **Data quality notes** (anything from the quality checklist that affected the analysis)

Make the most important point obvious within 10 seconds of reading. If the headline is "looks great but churn is accelerating," that line goes in the executive summary, not in the appendix.
