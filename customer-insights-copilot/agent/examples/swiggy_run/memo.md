# Swiggy (India, English Play Store reviews): customer insights memo

**Question:** What are customers most unhappy about, and what should be fixed first?  
**Data:** 99 usable reviews from 250 rows, 2026-11-03 to 2026-11-04  
**Model:** Claude Opus 5.5 in a claude.ai chat session (responses recorded, then replayed through the agent) · **Run:** 20261105-031559

> **Directional only:** fewer than 100 reviews, so shares have wide intervals.

## Answer

Customers are leaving mainly because support cannot fix failed orders: refunds are refused or swapped for coupons and the chatbot will not hand over to a person, while adding a cancel option and cash on delivery is the quickest win.

Unhelpful support and late, missing or wrong orders dominate the detailed reviews, and several reviewers say they have uninstalled or moved to a rival. One- and two-word reviews, which are mostly positive, were removed as too short, so this sample of detailed reviews leans more negative than the store rating.

Sentiment: 66% negative, 4% mixed, 30% positive.

## Priority ranking

| # | Theme | Mentions | Share (95% interval) | Avg rating | Says leaving | Trend | Type | Confidence | Priority |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Unhelpful support and refused refunds | 26 | 26% (19%–36%) | 1.0 | 19% | n/a | Major project | High | 0.44 |
| 2 | Late, missing or wrong orders | 20 | 20% (13%–29%) | 1.4 | 10% | n/a | Major project | High | 0.25 |
| 3 | Ordering and payment gaps | 6 | 6% (3%–13%) | 1.2 | 0% | n/a | Quick win | Medium | 0.12 |
| 4 | General dissatisfaction | 7 | 7% (3%–14%) | 1.0 | 0% | n/a | Major project | Medium | 0.09 |
| 5 | High prices and hidden charges | 9 | 9% (5%–16%) | 1.4 | 0% | n/a | Major project | Medium | 0.09 |
| 6 | Poor food quality and safety | 7 | 7% (3%–14%) | 1.7 | 0% | n/a | Major project | Medium | 0.08 |
| 7 | Safety and privacy concerns | 2 | 2% (1%–7%) | 1.0 | 50% | n/a | Major project | Low | 0.02 |
| 8 | What users like | 29 | 29% (21%–39%) | 4.8 | 0% | n/a | Strength | High | – |

Priority = share × impact × confidence ÷ effort. Impact comes from ratings and churn; effort is a judgment to validate with the team.

## Themes

### 1. Unhelpful support and refused refunds

- Evidence: “poor customer support when the food is not delivered” (f857548a-ce9c-47c6-bb02-bd4394f64023)
- Evidence: “they provide coupon but that coupon is no use” (a6243eb6-2c7c-43d3-931f-22e46161a521)
- Why (hypothesis): An AI-first support flow likely lacks a clear route to a human, and refund rules may favour restaurants over customers.
- Business impact: Turns a single failed order into a lost customer; this theme carries most of the churn signals.

### 2. Late, missing or wrong orders

- Evidence: “experienced delayed delivery of more then hour from there estimated shown time” (556187ad-42a1-427c-a3b3-28589ed1cc06)
- Evidence: “order lene ke 2 ghante bad Tak order mere ko nahin mila” (9ec0127b-e7c7-413b-9791-cde9a8473267)
- Why (hypothesis): Order batching and optimistic delivery estimates likely cause long delays, and restaurant-side cancellations may go unchecked.
- Business impact: Late or incomplete orders trigger most support contacts.

### 3. Ordering and payment gaps

- Evidence: “unable to open my cart” (613449c3-731b-4142-be61-0567e579a1d6)
- Evidence: “cash on delivery option ila ma iruku” (42f86acf-6630-41fc-8eb1-3ea42f3881fc)
- Why (hypothesis): Payment and cancellation options may have been reduced to cut costs, which locks some customers out.
- Business impact: Customers who need cash on delivery or a quick cancel cannot complete or fix an order.

### 4. General dissatisfaction

- Evidence: “worst app ever” (baca01f2-fae6-46d4-86c5-48baf2501f63)
- Evidence: “scam people” (6ba45bb7-90d9-41c8-bbb7-62b04840445c)
- Why (hypothesis): These customers likely had one of the problems above but did not describe it.
- Business impact: Strong negative sentiment that spreads through public ratings.

### 5. High prices and hidden charges

- Evidence: “why is your listed product price is not not matching with real price of product in store” (e8136eca-fc4c-47ec-9335-a988c9afff94)
- Evidence: “extra charges very bad application” (25c24383-3042-4b5f-a860-f9854f498834)
- Why (hypothesis): Layered fees and differences from store menu prices likely make the final bill feel unpredictable.
- Business impact: Price-sensitive customers may compare against rivals on every order.

### 6. Poor food quality and safety

- Evidence: “itna bekar khana jivan me nahi khaya mai” (ddb55cf7-8df6-4b7d-9aec-6fab80ba7ce5)
- Evidence: “too spicy not good food” (8092b238-9c2b-4bc0-ad90-50887fdeb757)
- Why (hypothesis): Some restaurant partners may not meet freshness, safety and packaging standards.
- Business impact: Unsafe food damages trust in the platform, not just the restaurant.

### 7. Safety and privacy concerns

- Evidence: “he was abusive and aggressive” (41fd9507-ec12-4133-86b1-86782dd40dee)
- Evidence: “app giving address to loan recovery agents” (70d79119-0bf5-464e-af32-56a536a8a9fe)
- Why (hypothesis): Rider conduct and data-sharing rules may not be enforced consistently.
- Business impact: Rare but serious; one reviewer uninstalled after an abusive delivery agent.

### 8. What users like

- Evidence: “good nice” (e5bf4134-6007-4ffd-8401-b02b86dfe240)
- Evidence: “very good app nd kind responsible for costumer” (64669e47-fa2a-4b07-9e59-ebf496ca8536)
- Why (hypothesis): Speed, value and convenience likely keep satisfied customers ordering.
- Business impact: A loyal base to protect while service failures are fixed.

## Recommendations

| Theme | Action | Owner | KPI | Effort (validate) |
|---|---|---|---|---|
| Unhelpful support and refused refunds | Add a guaranteed human handover after a failed chatbot attempt, and refund failed or incomplete orders by default. | Customer support operations | First-contact resolution rate | 3/5 |
| Late, missing or wrong orders | Cap batching on long routes, show realistic estimates, and penalise restaurants that cancel or short-deliver. | Delivery operations | On-time and complete-order rate | 4/5 |
| Ordering and payment gaps | Restore cash on delivery where possible and add a clear cancel window before the restaurant accepts. | Consumer app product team | Order completion rate | 2/5 |
| General dissatisfaction | Prompt low-rating reviewers for a reason so the cause can be tracked. | User research | Share of low ratings with a stated reason | 3/5 |
| High prices and hidden charges | Show the full price breakdown upfront and align listed prices with store prices. | Pricing and product | Repeat order rate | 4/5 |
| Poor food quality and safety | Audit partners with repeated food complaints and enforce packaging standards. | Restaurant partnerships | Food-quality complaint rate per restaurant | 3/5 |
| Safety and privacy concerns | Investigate both reports and publish a clear rider conduct and data-use policy. | Trust and safety | Safety incidents per order | 3/5 |
| What users like | Protect fast delivery and value pricing in future changes. | Product leadership | Share of positive reviews | 1/5 |

## Churn signals

5 of 99 reviews (5%) say the customer will leave, uninstall or switch.

Reviews: f857548a-ce9c-47c6-bb02-bd4394f64023, 41fd9507-ec12-4133-86b1-86782dd40dee, a6243eb6-2c7c-43d3-931f-22e46161a521, 556187ad-42a1-427c-a3b3-28589ed1cc06, 1629c5bf-40c2-417f-b6fc-f56ed5fcc5ae. The 'Says leaving' column shows which themes they sit in.

## Evaluation report

| Check | Type | Result | Detail |
|---|---|---|---|
| Quotes match their reviews word for word | hard | pass | all verified |
| Cited review IDs exist | hard | pass | all exist |
| No numbers written by the model | hard | pass | none |
| No financial claims | hard | pass | none |
| Action, owner and KPI for every issue | hard | pass | complete |
| No invented themes | hard | pass | none |
| Answer-first headline | hard | pass | present |
| Coverage: reviews in a named theme | soft | pass | 98% (target 85% or more) |
| 'Other' share | soft | pass | 2% (target 15% or less) |
| Reviews labelled | soft | pass | 99 of 99 (0 dropped) |
| Causes worded as hypotheses | soft | pass | yes |
| Sample size | soft | below target | 99 reviews (100 or more for firm results) |

## Data notes

- Removed 0 empty, 0 duplicate, 0 near-duplicate and 151 too-short rows.
- Masked 0 emails or phone numbers.

---

Should I break the support complaints down into refunds, chatbot loops and cancellation fees, or draft a human-handover policy?
