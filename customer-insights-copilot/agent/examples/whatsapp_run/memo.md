# WhatsApp (India, English Play Store reviews): customer insights memo

**Question:** What are users most unhappy about, and what should be fixed first?  
**Data:** 116 usable reviews from 250 rows, 2026-11-03 to 2026-11-04  
**Model:** Claude Opus 5.5 in a claude.ai chat session (responses recorded, then replayed through the agent) · **Run:** 20261105-031559

## Answer

Crashes and slowness, along with account lockouts, are what users complain about most, and bringing back the removed edit option is the quickest win.

Most reviews in this sample are positive, so complaints are a minority, but they cluster around two problems: the app crashing or loading slowly, and accounts being banned, left unverified or logged out. Many locked-out users still give high star ratings while asking for help, so rating-based severity likely understates how serious the lockouts are.

Sentiment: 32% negative, 9% mixed, 59% positive.

## Priority ranking

| # | Theme | Mentions | Share (95% interval) | Avg rating | Says leaving | Trend | Type | Confidence | Priority |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Bugs, crashes and slowness | 14 | 12% (7%–19%) | 2.9 | 0% | n/a | Deprioritize | High | 0.12 |
| 2 | Account bans and login lockouts | 16 | 14% (9%–21%) | 3.1 | 0% | n/a | Deprioritize | High | 0.10 |
| 3 | Removed or changed features | 5 | 4% (2%–10%) | 1.8 | 0% | n/a | Quick win | Medium | 0.07 |
| 4 | New feature requests | 6 | 5% (2%–11%) | 3.3 | 0% | n/a | Deprioritize | Medium | 0.03 |
| 5 | General dissatisfaction | 2 | 2% (0%–6%) | 1.0 | 50% | n/a | Major project | Low | 0.01 |
| 6 | Ads in the app | 1 | 1% (0%–5%) | 5.0 | 0% | n/a | Deprioritize | Low | 0.00 |
| 7 | What users like | 55 | 47% (39%–56%) | 4.7 | 0% | n/a | Strength | High | – |

Priority = share × impact × confidence ÷ effort. Impact comes from ratings and churn; effort is a judgment to validate with the team.

## Themes

### 1. Bugs, crashes and slowness

- Evidence: “Full of errors I've been trying to add a status for a week” (9f5c447d-82c5-47c5-af80-973dcb17a0ba)
- Evidence: “whatapp freezer and glitch” (8451edd3-6b7c-4e8f-9fab-be975e2ad09f)
- Why (hypothesis): Recent releases may have introduced stability and loading regressions, likely worse on low-end devices or weak networks.
- Business impact: Daily frustration that wears down trust in the app's reliability.

### 2. Account bans and login lockouts

- Evidence: “Stop messing with the account” (5c85d464-713b-4de9-a34d-d69d851909dd)
- Evidence: “my account has not been opening for few ago” (9db1f071-d7cb-42bc-9c58-0e03251c269e)
- Why (hypothesis): Automated spam detection likely flags some genuine users, and the appeal path may be unclear, so users plead for help in reviews instead.
- Business impact: Locked-out users lose access to all their contacts, the most severe experience in this sample.

### 3. Removed or changed features

- Evidence: “recently you removed the "edit" option and it's uncomfortable” (1cca8c9d-87a5-4b75-908f-0e00088ec165)
- Evidence: “Bio otomatick remove problem” (543362d9-6c23-40ac-a71b-d2c97d6cefe4)
- Why (hypothesis): Recent interface changes, such as removing message editing, likely shipped without enough user testing.
- Business impact: A small group, but with the lowest ratings in the sample.

### 4. New feature requests

- Evidence: “you will never get them back which is frustrating” (c1641835-7c24-4633-aec6-8d1b9e1f3ff1)
- Evidence: “I am disappointed that WhatsApp still lacks some basic but important privacy features” (e9c3a546-adc2-4fc9-bd38-eaf144f8bb9b)
- Why (hypothesis): Power users may want more control over privacy, backups and media quality than current settings allow.
- Business impact: Requests rather than blockers; useful input for the roadmap.

### 5. General dissatisfaction

- Evidence: “Just use Telegram” (3545f316-72ac-465d-b297-5e1b31b33554)
- Evidence: “Mark Zuckerberg what were u thinking” (27a988c6-5d71-4e39-9976-e03028cf92d1)
- Why (hypothesis): These users may have a specific problem they did not describe; the sample is too small to tell.
- Business impact: One reviewer tells others to use a rival app, a direct churn signal.

### 6. Ads in the app

- Evidence: “lately there's to may ads” (76afbb37-3e2b-4547-97f8-70af65c2f324)
- Why (hypothesis): Ad placements may have increased recently for some users.
- Business impact: A single mention, so this is anecdotal.

### 7. What users like

- Evidence: “It's just amazing” (c7395dad-ff88-4c6d-9b94-c645ce6a0f4d)
- Evidence: “it's a good app ,easy to use and efficient.” (18c70348-1af8-455b-ba41-617d04766e1a)
- Why (hypothesis): Simplicity, reliability and free communication likely drive loyalty.
- Business impact: A strong base of satisfied users to protect while the issues are fixed.

## Recommendations

| Theme | Action | Owner | KPI | Effort (validate) |
|---|---|---|---|---|
| Bugs, crashes and slowness | Track crash and slow-load rates by app version and device, and fix the top regressions first. | Android engineering | Crash-free session rate | 3/5 |
| Account bans and login lockouts | Audit false-positive bans and add a clear in-app appeal with status updates. | Trust and safety | Appeal resolution time | 4/5 |
| Removed or changed features | Restore the edit option and make the new pin and reaction-bar behaviour optional. | Messaging product team | Rating among reviews that mention editing | 2/5 |
| New feature requests | Log these requests and test demand for backup recovery and privacy controls. | Product management | Feature request volume by topic | 4/5 |
| General dissatisfaction | Follow up with short surveys to find the specific cause. | User research | Share of reviews that name a specific problem | 3/5 |
| Ads in the app | Monitor ad complaints before acting. | Monetization team | Share of reviews mentioning ads | 3/5 |
| What users like | Protect simplicity and reliability in every future change. | Product leadership | Share of positive reviews | 1/5 |

## Churn signals

1 of 116 reviews (1%) say the customer will leave, uninstall or switch.

Reviews: 3545f316-72ac-465d-b297-5e1b31b33554. The 'Says leaving' column shows which themes they sit in.

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
| Coverage: reviews in a named theme | soft | below target | 82% (target 85% or more) |
| 'Other' share | soft | below target | 18% (target 15% or less) |
| Reviews labelled | soft | pass | 116 of 116 (0 dropped) |
| Causes worded as hypotheses | soft | pass | yes |
| Sample size | soft | pass | 116 reviews (100 or more for firm results) |

## Data notes

- Removed 0 empty, 0 duplicate, 0 near-duplicate and 134 too-short rows.
- Masked 0 emails or phone numbers.

---

Should I split the lockout reviews into bans, verification failures and logouts, or draft an improved appeal flow?
