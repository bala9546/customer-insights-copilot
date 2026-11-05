# Customer Insights Agent (Python)

Turns a CSV of customer reviews into an answer-first, prioritised brief, and checks its own output before delivering it.

**Design rule:** the model labels text and writes prose; code does every count, interval, ranking and check; a human approves the theme list before anything is counted.

**Real-data runs:** 250 Play Store reviews each of WhatsApp ([memo](examples/whatsapp_run/memo.md)) and Swiggy ([memo](examples/swiggy_run/memo.md)); all hard checks passed. An offline demo run on illustrative data is in [`examples/sample_run/memo.md`](examples/sample_run/memo.md).

## Three ways to run it

| Mode | Command flag | Needs | Use it for |
| --- | --- | --- | --- |
| Mock | `--model mock` | Nothing | Checking your CSV loads and the pipeline works (keyword rules, not real analysis) |
| Claude | `--model claude` | `pip install anthropic` and `ANTHROPIC_API_KEY` | Live analysis of your own data |
| Replay | `--model replay --replay-dir <folder>` | A folder with `codebook.json`, `labels.json`, `brief.json` | Re-running recorded model responses through the full pipeline, so results can be reproduced and audited |

### Check your file (no API key)

```bash
cd agent
python agent.py --data sample_reviews.csv --company "FreshBite" \
  --question "Why are we losing repeat customers?" --model mock --auto-approve
```

The memo and every intermediate file land in `runs/<run id>/`.

### Live run with Claude

1. Create a key at console.anthropic.com and run `pip install anthropic`.
2. Set the key in your terminal (never commit it):
   - macOS or Linux: `export ANTHROPIC_API_KEY=your-key`
   - Windows PowerShell: `$env:ANTHROPIC_API_KEY="your-key"`
3. Run without `--auto-approve`, so you review the theme list:

```bash
python agent.py --data my_reviews.csv --company "Your company" \
  --question "What should we fix first?" --model claude
```

Override the model with `--model-name` or the `CLAUDE_MODEL` environment variable.

### Replay

`--model replay` reads the model's three outputs from a folder instead of calling an API. Everything else (verification, counting, intervals, scoring, brief checks) runs exactly as in a live run, and two replays of the same folder give identical numbers. An optional `source.txt` in the folder names who produced the responses; it is printed in the memo.

## Your CSV

Only two columns are required: an id and the review text. Extra columns unlock more metrics.

| Column (any of these names) | Required | Unlocks |
| --- | --- | --- |
| `review_id`, `id` | yes | Citations |
| `text`, `review`, `comment`, `content`, `feedback` | yes | Everything |
| `rating`, `stars`, `score` (1–5) | no | Rating gap, impact from ratings, full confidence |
| `date` (YYYY-MM-DD) | no | 30-day trend |

Name columns (`user_name`, `author`, …) are dropped automatically. Missing columns are skipped and noted in the memo; nothing is invented.

## The 9 steps

| Step | Done by | What happens |
| --- | --- | --- |
| 1 Load and clean | Code | Dedupe, drop near-copies and one- or two-word reviews, mask emails and phone numbers, flag prompt injection, stop if under 30 usable reviews |
| 2 Propose codebook | Model | 5 to 8 themes from a fixed 30-review sample |
| 3 Approve codebook | You | Approve, edit `codebook.json`, or reject with feedback (2 rejections stop the run) |
| 4 Label reviews | Model | Theme, sentiment, journey stage, churn intent, verbatim evidence; batches of 20 |
| 5 Verify labels | Code | Theme in codebook, valid fields, evidence word for word; failures are redone up to 2 times |
| 6 Aggregate and score | Code | Share, 95% Wilson interval, rating gap, churn share, trend, RICE-style priority |
| 7 Write the brief | Model | Headline, hypotheses, impact, action, owner, KPI, with no numbers |
| 8 Check the brief | Code | No model-written numbers, no money claims, owner and KPI for every issue; redone up to 2 times |
| 9 Deliver | Code | `memo.md` with tables, evidence and an evaluation report |

## Files in a run folder

`quality_report.json`, `codebook.json`, `labels.json`, `metrics.json`, `metrics.csv`, `brief.json`, `eval_report.json`, `memo.md`, and `run_log.jsonl` (every step with time, model and tokens used).

## Human evaluation (do this once)

```bash
python compare_gold.py template --data my_reviews.csv --out gold.csv   # 50 reviews to label yourself
python compare_gold.py score --gold gold.csv --labels runs/<run id>/labels.json
```

It reports agreement and Cohen's kappa (0.6 or more is a common bar for good agreement).

## Tests

```bash
python -m unittest discover tests
```

## Options

`--min-reviews 30` · `--batch-size 20` · `--max-tokens 400000` (budget cap) · `--runs-dir runs` · `--mock-faults` (mock only: injects bad quotes to show the retry loop)

## Limits

- The checks prove grounding (every quote and number traces to data), not that a theme is the right one; the human codebook review and gold-set comparison cover that.
- Under 100 reviews, results are marked directional.
- Effort scores are model judgments, marked "validate with the team".
- Names written inside review text are not masked; drop such reviews or redact them first.

See [AGENT_SPEC.md](AGENT_SPEC.md) for the persona, grounding rules, guardrails and success criteria.
