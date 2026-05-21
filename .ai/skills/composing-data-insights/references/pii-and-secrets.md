# PII and Secrets Handling

Sensitive fields detected in user-supplied data must be confirmed with the user and aggregated / masked / excluded **before** any field enters the HTML body or the image prompt. The image prompt is the highest-risk surface because the rendered PNG is opaque to redaction tools after the fact.

This is a **blocking step** in the Default Workflow (Step 2) — do not proceed to insights / risks / rendering until the sensitivity check is complete.

## Detection

Scan the user-supplied data for:

### Direct PII

- **Person names** — full names, given+family, especially in customer / employee tables
- **Customer / company names** — when the dataset is a customer list or per-account metrics
- **Email addresses** — anything matching `<local>@<domain>.<tld>`
- **Phone numbers** — any sequence that could be a phone number (10+ digits, common separators)
- **Postal addresses** — street + city + region patterns
- **Government IDs** — SSN / national ID / passport / driver's license patterns
- **Date of birth** — explicit DOB columns or `born_*` style fields

### Secrets

- **API tokens** — long opaque strings, especially with prefixes (`sk-`, `pk_`, `ghp_`, `Bearer `, `xoxb-`, `AKIA*`, etc.)
- **Passwords** — anything in a column named `password` / `passwd` / `pwd` / `secret`, even if hashed
- **Private keys** — content matching `-----BEGIN ... PRIVATE KEY-----`
- **Connection strings** — URIs with embedded credentials (`postgres://user:pass@host/db`)
- **Internal IDs that look like credentials** — UUIDs in `*_token` / `*_secret` columns

### Borderline (ask the user)

- **Internal customer IDs** — usually safe but treat as PII if combined with revenue
- **Geographic detail at low aggregation** — postal code + age bracket + gender = re-identifiable
- **Free-text notes columns** — may contain anything; treat as PII by default if present

## Confirmation Step

If any of the above is detected:

1. **Stop the workflow.** Do not proceed to insights or rendering yet.
2. **Tell the user what was found**, by category and column. Example:
   > 数据里发现了潜在敏感字段：`customer_email` (邮箱), `customer_full_name` (姓名), `card_last4` (卡号尾号)。在生成报告前需要确认你希望怎么处理：
3. **Ask explicitly how to proceed**, offering these options:
   - **Aggregate** — drop the row-level identity, keep only group-level metrics ("top 5 segments by revenue", not "top 5 customers")
   - **Mask** — replace with format-preserving placeholders (`a***@example.com`, `Customer #1234`, `***-***-1234`)
   - **Exclude** — drop the column from the analysis entirely
   - **Pseudonymize** — replace with stable but non-reversible labels (`Customer-A`, `Customer-B`)
4. **Wait for explicit user confirmation.** Do not silently default to any option.

## Application Rules

Once the user has chosen handling for each sensitive field:

### HTML body

- Apply the chosen handling at the field level
- Never include raw email / phone / name / token in any HTML element, even commented out
- For `<table>` rendering, replace cell values with the masked / pseudonymized form
- Tooltip / `title` attributes also count — sanitize them

### Image prompt

- The image prompt is the **strictest** surface — once a value enters the prompt, it can be rendered into the PNG and is irreversible
- **Never include raw PII in the prompt**, even if the user said "OK to include in HTML"
- Default to aggregated / masked values in the prompt regardless of HTML handling, unless the user has explicitly opted into raw values for the image
- Example: HTML may show `Customer A: $4.2M revenue`; image prompt should say `top customer: $4.2M revenue` (no per-customer label)

### Logs / temp files

- The temp prompt file (`mktemp -t composing-prompt.XXXXXX`) contains the prompt — apply the same masking before writing
- Always `rm -f` the temp file after the script returns, success or failure
- Do not echo the prompt to chat in clear text if it contains any sensitive value (even a masked one — masking can be incomplete)

## What Not to Do

- **Don't** silently strip or rename sensitive columns without telling the user — they may legitimately need that field
- **Don't** "pseudonymize" by hashing the value into the prompt — hashes still leak ordering, can be cracked for short fields, and are not human-readable for the report
- **Don't** rely on prompt-side guardrails ("the model won't output raw values") — the model has no PII model; it will faithfully render whatever you put in
- **Don't** assume "internal data" means "non-sensitive" — internal customer lists, employee tables, and connection strings all count

## Quick Decision Tree

```
data has PII / secrets?
├── no  → continue with normal workflow
└── yes → stop, list what was found, ask user
         ├── user picks aggregate  → re-aggregate above the identity level
         ├── user picks mask       → format-preserving placeholders
         ├── user picks pseudonymize → stable labels (Customer-A, B, ...)
         └── user picks exclude    → drop column entirely
         then continue, applying chosen handling to HTML
         AND defaulting image prompt to aggregated / masked even if HTML kept more
```

When in doubt: **less in the prompt, more in the HTML**. The HTML is editable / regeneratable; the PNG is not.
