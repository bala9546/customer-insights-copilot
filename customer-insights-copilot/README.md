# Customer Insights to Recommendations

An AI tool that turns raw customer feedback into an answer-first, consulting-style brief: quantified themes, verified evidence, root-cause hypotheses, impact-vs-effort priorities, and an automatic check on whether the AI's own output can be trusted.

**Live demo:** https://bala9546.github.io/customer-insights-copilot/ (opens on the real-data results, with a light/dark theme switch; no API key needed)

**Agent version (Python):** see [agent/README.md](agent/README.md). Runs offline in mock mode, replays recorded model responses, or calls Claude with your own key.

## Tested on real data
Two runs with the Python agent on **250 real Google Play reviews each** (India, English, 3–4 Nov 2026). Explore both on the live site, or read the memos: [WhatsApp](agent/examples/whatsapp_run/memo.md) · [Swiggy](agent/examples/swiggy_run/memo.md).

| | WhatsApp | Swiggy |
|---|---|---|
| Usable reviews | 116 of 250 | 99 of 250 |
| Negative sentiment | 32% | 66% |
| Top issue | Account bans and login lockouts (14%) | Unhelpful support and refused refunds (26%) |
| Quick win | Restore the removed message-edit option | Add a cancel option and cash on delivery |
| Say they are leaving | 1 (1%) | 5 (5%) |
| Hard checks passed | 7 of 7 | 7 of 7 |
| Soft checks below target | Coverage 82% (many reviews are names or single words) | Sample size 99 (just under 100) |

**What the runs taught me**
- **WhatsApp:** many locked-out users still give five stars while pleading for their account back, so a rating-based impact score understates lockouts. A human reviewer should weigh them higher than the score suggests.
- **Swiggy:** all 5 reviewers who say they are leaving also complain about support, refunds or the chatbot. Fixing what happens after a failed order matters more than the failure itself.
- **The data improved the agent:** most short reviews are repeats like "good", which first tripped the duplicate check and stopped the Swiggy run. The cleaner now removes short reviews before counting duplicates.

**How the runs were produced:** the model steps (theme list, labels, brief) were done by Claude Opus 5.5 in a chat session, recorded, and replayed through the agent (`--model replay`). Every count, interval, quote check and priority score was computed by the agent's code. The raw reviews and per-review labels are not republished.

## The problem
Feedback arrives as hundreds of unstructured reviews, tickets and comments. A manager or consultant must turn it into a decision, and an AI summary is useless if it cannot be checked ("users are unhappy" with no source).

## What it does
1. Takes a client question plus raw feedback (one item per line).
2. Returns an **answer-first summary** with a one-line sentiment split.
3. Groups feedback into mutually exclusive themes, with counts computed **in code**, verified quotes, a **root-cause hypothesis** and **business impact**.
4. Ranks themes by `frequency x severity / effort`, tags them (Quick win / Major project / Fill-in / Deprioritize), and rates each **High/Medium/Low confidence**.
5. Gives recommendations with **action, owner and KPI**, lists churn signals, and exports an executive memo.

## Eval layer (the core of the project)
| Check | How it works | Failure it catches |
|---|---|---|
| Quote verification | Each evidence quote must appear word for word in a cited review | Fabricated evidence |
| Citation validity | Cited review IDs must exist | Hallucinated sources |
| Coverage | Share of feedback assigned to at least one theme | Silently dropped data |
| Action completeness | Every recommendation needs an owner and a KPI | Vague advice nobody owns |
| Anecdote flag | Themes backed by a single review are flagged | Over-generalising one voice |
| Sample-size warning | Warns below 30 items | False statistical confidence |

**Good vs bad output.** Bad: "Users dislike delivery." Good: "3 of 16 items (19%) report delivery over 60 minutes; quote and source IDs attached."

## Known limitations
- Theme assignment still depends on the LLM; the evals check grounding, not whether a theme is the right one.
- Small samples give directional results only.
- The web app's Live mode calls the API from the browser with your own key (kept in memory, never stored). The Python agent is the safer route for real data.

## How it was built
Built with AI assistance under my direction: I chose the problem, set the requirements (consulting-style output, source-cited claims, automated evals), reviewed the outputs and shipped the project. Claude wrote the code.

## Roadmap
Review samples spanning several weeks (to measure trends), a live-model run to compare against these replays, my own 50-review gold-set check, CSV upload in the web app.
