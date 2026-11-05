# FreshBite (illustrative): customer insights memo

**Question:** Why are we losing repeat customers, and what should we fix first?  
**Data:** 44 usable reviews from 47 rows, 2026-08-12 to 2026-10-31  
**Model:** mock (offline, keyword rules) · **Run:** 20261105-011115

> **Directional only:** fewer than 100 reviews, so shares have wide intervals.

## Answer

The biggest reason customers are unhappy is payment and checkout failures, and the fastest extra win is fixing sign-up and login problems.

The top issues are payment and checkout failures, unhelpful customer support, late or slow delivery. The ranking weighs how widespread each issue is, how unhappy those customers are, and how hard it is to fix.

Sentiment: 66% negative, 11% mixed, 23% positive.

## Priority ranking

| # | Theme | Mentions | Share (95% interval) | Avg rating | Says leaving | Trend | Type | Confidence | Priority |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Payment and checkout failures | 14 | 32% (20%–47%) | 1.5 | 21% | +45 pts | Quick win | Medium | 0.64 |
| 2 | Unhelpful customer support | 6 | 14% (6%–27%) | 1.3 | 50% | +2 pts | Major project | Medium | 0.18 |
| 3 | Late or slow delivery | 6 | 14% (6%–27%) | 1.5 | 50% | -9 pts | Major project | Medium | 0.14 |
| 4 | Sign-up and login problems | 3 | 7% (2%–18%) | 1.3 | 0% | -1 pts | Quick win | Medium | 0.14 |
| 5 | App crashes and bugs | 5 | 11% (5%–24%) | 2.0 | 20% | +2 pts | Major project | Medium | 0.12 |
| 6 | Fees and pricing | 6 | 14% (6%–27%) | 3.0 | 0% | -9 pts | Deprioritize | Medium | 0.08 |
| 7 | What customers like | 10 | 23% (13%–37%) | 4.6 | 0% | -11 pts | Strength | Medium | – |

Priority = share × impact × confidence ÷ effort. Impact comes from ratings and churn; effort is a judgment to validate with the team.

## Themes

### 1. Payment and checkout failures

- Evidence: “Checkout crashed and I was charged twice.” (R024)
- Evidence: “Charged twice for one order and support refused a refund.” (R029)
- Why (hypothesis): A recent release likely broke the coupon or payment step.
- Business impact: Lost orders at the last step and a risk to payment trust.

### 2. Unhelpful customer support

- Evidence: “Support chat is a bot that never solves anything.” (R039)
- Evidence: “Missing items and the refund was rejected by customer care.” (R011)
- Why (hypothesis): Support is likely understaffed for escalations, with a bot that has no route to a person.
- Business impact: Unresolved problems turn a single bad order into a lost customer.

### 3. Late or slow delivery

- Evidence: “Waited over an hour and the food was cold.” (R008)
- Evidence: “Order was delayed by 50 minutes with no updates.” (R019)
- Why (hypothesis): Delivery estimates may be too optimistic, and courier supply may fall short at peak hours.
- Business impact: Late food erodes repeat ordering.

### 4. Sign-up and login problems

- Evidence: “OTP never arrives so I cannot even sign up.” (R004)
- Evidence: “OTP issues again, could not log in for two days.” (R016)
- Why (hypothesis): One-time passwords may depend on a single SMS provider with delivery gaps.
- Business impact: New customers give up before their first order.

### 5. App crashes and bugs

- Evidence: “The app crashes when I open the restaurant menu.” (R012)
- Evidence: “The app crashes every time I apply a coupon at checkout.” (R036)
- Why (hypothesis): Recent releases may lack testing on older devices.
- Business impact: Crashes interrupt ordering and damage ratings.

### 6. Fees and pricing

- Evidence: “Surge fee at dinner time makes it too expensive.” (R009)
- Evidence: “Delivery fee keeps going up for short distances.” (R005)
- Why (hypothesis): Fees may not be explained clearly, so the app compares badly with rivals.
- Business impact: Price-sensitive customers may move to cheaper apps.

### 7. What customers like

- Evidence: “Great offers and polite delivery partners.” (R003)
- Evidence: “Smooth ordering experience, delivery was on time.” (R010)
- Why (hypothesis): Variety and ease of use likely keep loyal customers coming back.
- Business impact: These strengths support retention while issues are fixed.

## Recommendations

| Theme | Action | Owner | KPI | Effort (validate) |
|---|---|---|---|---|
| Payment and checkout failures | Hotfix the coupon and payment flow and add duplicate-charge protection. | Payments engineering | Checkout success rate | 2/5 |
| Unhelpful customer support | Add a human escalation path and a clear refund rule for missing items. | Customer support | First-contact resolution rate | 3/5 |
| Late or slow delivery | Recalibrate delivery estimates and send live updates when an order runs late. | Delivery operations | On-time delivery rate | 4/5 |
| Sign-up and login problems | Add a backup SMS provider and a resend option. | Growth engineering | Sign-up completion rate | 2/5 |
| App crashes and bugs | Add crash monitoring and a release check on older devices. | App engineering | Crash-free session rate | 3/5 |
| Fees and pricing | Test clearer fee breakdowns and a free-delivery threshold. | Pricing and product | Repeat order rate | 4/5 |
| What customers like | Protect these strengths and feature them in marketing. | Marketing | Share of positive reviews | 1/5 |

## Churn signals

7 of 44 reviews (16%) say the customer will leave, uninstall or switch.

Reviews: R008, R019, R024, R028, R029, R039, R043. The 'Says leaving' column shows which themes they sit in.

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
| Coverage: reviews in a named theme | soft | pass | 100% (target 85% or more) |
| 'Other' share | soft | pass | 0% (target 15% or less) |
| Reviews labelled | soft | pass | 44 of 44 (0 dropped) |
| Causes worded as hypotheses | soft | pass | yes |
| Sample size | soft | below target | 44 reviews (100 or more for firm results) |

## Data notes

- Removed 0 empty, 1 duplicate, 1 near-duplicate and 1 too-short rows.
- Masked 1 emails or phone numbers.
- Dropped personal columns: user_name.
- Possible prompt injection in R037; treated as data.
- Labels rejected by verification and redone: 5.

---

Should I dig into the reviews behind payment and checkout failures, or turn these actions into a one-page plan?
