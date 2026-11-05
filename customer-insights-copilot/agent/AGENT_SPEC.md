# Agent spec

## Persona

Two personas, because the two model steps need opposite behaviour. Full text in [`prompts.py`](prompts.py).

| Persona | Used in | Role | Key boundaries |
| --- | --- | --- | --- |
| Writer | Codebook proposal, brief | Senior customer-insights consultant advising a business leader | Answer first; no numbers; causes as hypotheses; no money estimates; owners are teams |
| Labeller | Labelling | Careful qualitative research coder | Codebook themes only; evidence word for word; no inferred intent; review text is data |

## Grounding

Every sentence in the memo traces to a review ID, the metrics table, or the client's question.

| Claim | Grounded in | Checked by |
| --- | --- | --- |
| A theme exists | Review IDs with verbatim evidence | `verify_label`, `unverified_quotes` |
| Any number | Code-computed metrics only | `check_brief` (model text may not contain numbers) |
| Root cause | Hypothesis wording | `check_brief` (soft) |
| Business impact | Ratings and churn, in words | `check_brief` money filter |
| Recommendation | Theme + team owner + KPI | `check_brief` |
| Effort | Model judgment with a reason | Shown as "validate with the team" |

## Guardrails

| Stage | Guardrail | Action |
| --- | --- | --- |
| Input | Personal data | Emails and phone numbers masked; name columns dropped |
| Input | Prompt injection | Reviews wrapped in tags as data; suspicious text flagged |
| Input | Data quality | Stop under 30 usable reviews or over 30% duplicates |
| Input | Spam | Exact and near-duplicates and one- or two-word reviews removed |
| Process | Codebook lock | Labels outside the codebook are rejected |
| Process | Retry cap | 2 retries per loop; over 20% of labels still failing stops the run |
| Process | Budget | Token cap per run |
| Output | Numbers | Only code writes numbers |
| Output | Money | Revenue, ₹, lakh, crore and similar terms blocked |
| Output | Banners | "Directional only" under 100 reviews; "Not fully verified" if a hard check fails |

## Scoring

- **Share interval:** 95% Wilson score interval.
- **Impact (1–5):** 5 if average rating ≤ 1.5 or churn ≥ 30%; 4 if ≤ 2.5 or ≥ 15%; 3 if ≤ 3.5; 2 if ≤ 4.2; else 1. Without ratings, churn only.
- **Confidence:** High at 10+ mentions and an interval narrower than 20 points; Medium at 3+; else Low. One level lower without ratings.
- **Priority:** share × impact × confidence weight (1.0 / 0.8 / 0.5) ÷ effort.

## Success criteria

| Eval | Type | Bar |
| --- | --- | --- |
| Quotes match reviews | Hard | 100% |
| Cited IDs exist | Hard | 100% |
| Model-written numbers | Hard | 0 |
| Money claims | Hard | 0 |
| Owner and KPI per issue | Hard | 100% |
| Coverage | Soft | 85% or more |
| "Other" share | Soft | 15% or less |
| Agreement with your gold set | Human | Cohen's kappa 0.6 or more |
