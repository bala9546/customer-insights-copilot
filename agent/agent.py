"""Customer Insights Agent: the harness.

Runs a fixed 9-step plan:
  1 load and clean (code)        2 propose codebook (model)   3 approve codebook (human)
  4 label every review (model)   5 verify labels (code)       6 aggregate and score (code)
  7 write the brief (model)      8 check the brief (code)     9 deliver memo and eval report (code)
Steps 4-5 and 7-8 repeat up to 2 times when checks fail. Everything is saved in a run folder.

Usage:
  python agent.py --data sample_reviews.csv --company "FreshBite" \
      --question "Why are we losing repeat customers?" --model mock --auto-approve
"""
import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from llm import ModelError, get_model
from prompts import LABELLER_PERSONA, WRITER_PERSONA, brief_prompt, codebook_prompt, label_prompt
from tools import (NUMBER, QualityGateError, aggregate, check_brief, load_reviews, sample_reviews,
                   score, unverified_quotes, validate_codebook, verify_label)

MAX_RETRIES = 2


class StopRun(Exception):
    """A stop condition was reached; the agent hands back to the human."""


class RunLog:
    def __init__(self, path, model):
        self.path, self.model, self.start = path, model, time.time()

    def write(self, step, status, **detail):
        entry = {"time": datetime.now().isoformat(timespec="seconds"), "step": step, "status": status,
                 "model": self.model.name, "tokens_total": self.model.tokens_used, **detail}
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[{step}] {status}" + (f" ({detail.get('note')})" if detail.get("note") else ""))


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def check_budget(model, cap):
    if model.tokens_used > cap:
        raise StopRun(f"Token budget of {cap} reached. Partial results are in the run folder.")


# ---------------------------------------------------------------- steps 2-3

def ask_human(codebook, path):
    print("\nProposed codebook (you approve this before anything is counted):")
    for t in codebook["themes"]:
        if t["id"] != "other":
            print(f"  - {t['name']} [{t['id']}], effort {t['effort']}: {t['definition']}")
    try:
        choice = input(f"\nApprove [a], edit {path.name} and then approve [e], or reject [r]: ").strip().lower()
        if choice.startswith("r"):
            return "reject", input("What should change? ").strip()
        if choice.startswith("e"):
            input(f"Edit {path} now, save it, then press Enter... ")
            return "edit", None
        return "approve", None
    except EOFError:
        raise StopRun("No one is here to approve the codebook. Re-run interactively or use --auto-approve.")


def get_codebook(model, reviews, args, run_dir, log):
    sample, feedback, rejections = sample_reviews(reviews), None, 0
    path = run_dir / "codebook.json"
    for _ in range(3):
        raw = model.complete_json("propose_codebook", WRITER_PERSONA,
                                  codebook_prompt(args.company, args.question, sample, feedback),
                                  {"sample": sample})
        check_budget(model, args.max_tokens)
        try:
            codebook = validate_codebook(raw)
        except ValueError as exc:
            feedback = str(exc)
            log.write("2 propose codebook", "invalid", note=feedback)
            continue
        save(path, codebook)
        log.write("2 propose codebook", "ok", note=f"{len(codebook['themes']) - 1} themes")
        if args.auto_approve:
            log.write("3 approve codebook", "auto-approved", note="--auto-approve was set")
            return codebook
        decision, feedback = ask_human(codebook, path)
        if decision == "edit":
            codebook = validate_codebook(json.loads(path.read_text(encoding="utf-8")))
            save(path, codebook)
        if decision in ("approve", "edit"):
            log.write("3 approve codebook", decision + "d by human")
            return codebook
        rejections += 1
        log.write("3 approve codebook", "rejected", note=feedback)
        if rejections >= 2:
            break
    raise StopRun("The codebook was rejected twice or could not be built. Review the sample data and try again.")


# ---------------------------------------------------------------- steps 4-5

def label_all(model, reviews, codebook, args, log):
    by_id = {r["id"]: r for r in reviews}
    theme_ids = {t["id"] for t in codebook["themes"]}
    labels, pending, feedback, rejected = {}, list(reviews), {}, 0
    failed = {}
    for round_no in range(MAX_RETRIES + 1):
        failed = {}
        for i in range(0, len(pending), args.batch_size):
            batch = pending[i:i + args.batch_size]
            batch_ids = {r["id"] for r in batch}
            notes = {rid: feedback[rid] for rid in batch_ids if rid in feedback} or None
            try:
                out = model.complete_json("label_batch", LABELLER_PERSONA, label_prompt(codebook, batch, notes),
                                          {"batch": batch, "codebook": codebook})
            except ModelError as exc:
                failed.update({rid: [f"model error: {exc}"] for rid in batch_ids})
                continue
            check_budget(model, args.max_tokens)
            returned = {lab.get("review_id"): lab for lab in out.get("labels", [])
                        if isinstance(lab, dict) and lab.get("review_id") in batch_ids}
            for review in batch:
                label = returned.get(review["id"])
                problems = ["no label returned"] if label is None else verify_label(label, by_id, theme_ids)
                if problems:
                    failed[review["id"]] = problems
                else:
                    stage = label.get("journey_stage")
                    labels[review["id"]] = {
                        "review_id": review["id"], "themes": label["themes"], "sentiment": label["sentiment"],
                        "journey_stage": stage if isinstance(stage, str) and stage else None,
                        "churn_intent": label["churn_intent"], "evidence": label["evidence"].strip(),
                    }
        rejected += len(failed)
        step = "4-5 label and verify" + (f" (retry {round_no})" if round_no else "")
        log.write(step, "ok" if not failed else "some labels failed",
                  note=f"{len(labels)} verified, {len(failed)} failed", failed=failed)
        if not failed:
            break
        feedback, pending = failed, [by_id[rid] for rid in failed]
    report = {"verified": len(labels), "rejected_attempts": rejected, "dropped": sorted(failed)}
    if len(failed) > 0.20 * len(reviews):
        raise StopRun(f"{len(failed)} of {len(reviews)} reviews still fail validation after {MAX_RETRIES} retries. "
                      "Check the codebook or the data.")
    return labels, report


# ---------------------------------------------------------------- steps 7-8

def words_for(theme):
    share, impact = theme["share"], theme["impact"]
    churn = theme["churn_share"]
    trend = theme["trend"]
    return {
        "id": theme["id"], "name": theme["name"], "type": theme["type"], "quadrant": theme["quadrant"],
        "confidence": theme["confidence"],
        "how_common": "very common" if share >= 0.30 else "common" if share >= 0.15
        else "occasional" if share >= 0.07 else "rare",
        "severity": {5: "severe", 4: "high", 3: "moderate", 2: "low", 1: "minimal"}[impact],
        "leaving": "many of these customers say they will leave" if churn >= 0.30
        else "some say they will leave" if churn >= 0.10 else "a few say they will leave" if churn > 0
        else "none say they will leave",
        "trend": "unknown" if trend is None else "rising" if trend >= 0.05 else "falling" if trend <= -0.05
        else "stable",
        "effort": {1: "very low", 2: "low", 3: "medium", 4: "high", 5: "very high"}[theme["effort"]],
        "example_quote": theme["evidence"][0]["quote"] if theme["evidence"] else "",
    }


def write_and_check(model, metrics, args, log):
    facts = [words_for(t) for t in metrics["themes"] if t["mentions"]]
    allowed = set(NUMBER.findall(args.question + " " + args.company))
    feedback, hard, soft, brief = None, [], [], {}
    for attempt in range(MAX_RETRIES + 1):
        brief = model.complete_json("write_brief", WRITER_PERSONA,
                                    brief_prompt(args.company, args.question, facts, feedback), {"facts": facts})
        check_budget(model, args.max_tokens)
        hard, soft = check_brief(brief, metrics, allowed)
        step = "7-8 write and check brief" + (f" (retry {attempt})" if attempt else "")
        log.write(step, "pass" if not hard else "failed checks", note="; ".join(hard) or None)
        if not hard:
            break
        feedback = hard
    return brief, hard, soft


# ---------------------------------------------------------------- step 9

def pct(x):
    return f"{x * 100:.0f}%"


def build_eval(metrics, reviews_by_id, hard, soft, label_report, quality):
    def failed(prefix):
        return [h for h in hard if h.startswith(prefix)]
    cited = {e["review_id"] for t in metrics["themes"] for e in t["evidence"]} | set(metrics["churn_ids"])
    bad_quotes = unverified_quotes(metrics, reviews_by_id)
    checks = [
        ("Quotes match their reviews word for word", "hard", not bad_quotes, bad_quotes or "all verified"),
        ("Cited review IDs exist", "hard", cited <= set(reviews_by_id), "all exist"),
        ("No numbers written by the model", "hard", not failed("numbers"), failed("numbers") or "none"),
        ("No financial claims", "hard", not failed("financial"), failed("financial") or "none"),
        ("Action, owner and KPI for every issue", "hard",
         not [h for h in hard if "missing" in h or h.startswith("no recommendation")],
         [h for h in hard if "missing" in h or h.startswith("no recommendation")] or "complete"),
        ("No invented themes", "hard", not failed("themes not in"), failed("themes not in") or "none"),
        ("Answer-first headline", "hard", not failed("headline"), "present" if not failed("headline") else "empty"),
        ("Coverage: reviews in a named theme", "soft", metrics["coverage"] >= 0.85,
         f"{pct(metrics['coverage'])} (target 85% or more)"),
        ("'Other' share", "soft", metrics["other_share"] <= 0.15, f"{pct(metrics['other_share'])} (target 15% or less)"),
        ("Reviews labelled", "soft", not label_report["dropped"],
         f"{label_report['verified']} of {quality['usable']} ({len(label_report['dropped'])} dropped)"),
        ("Causes worded as hypotheses", "soft", not soft, soft or "yes"),
        ("Sample size", "soft", quality["usable"] >= 100, f"{quality['usable']} reviews (100 or more for firm results)"),
    ]
    return [{"check": c, "type": t, "passed": bool(p), "detail": d} for c, t, p, d in checks]


def render_memo(args, model, quality, metrics, brief, evals, label_report, run_id):
    themes = [t for t in metrics["themes"] if t["mentions"]]
    by_theme = {t.get("id"): t for t in brief.get("themes", [])}
    hard_ok = all(e["passed"] for e in evals if e["type"] == "hard")
    lines = [f"# {args.company}: customer insights memo", "",
             f"**Question:** {args.question}  ",
             f"**Data:** {quality['usable']} usable reviews from {quality['raw_rows']} rows"
             + (f", {quality['date_range'][0]} to {quality['date_range'][1]}" if quality["date_range"] else "")
             + f"  \n**Model:** {model.name} · **Run:** {run_id}", ""]
    if quality["usable"] < 100:
        lines += ["> **Directional only:** fewer than 100 reviews, so shares have wide intervals.", ""]
    if not hard_ok:
        lines += ["> **Not fully verified:** some hard checks failed after 2 retries. See the evaluation report.", ""]

    lines += ["## Answer", "", brief.get("headline", ""), "", brief.get("summary", ""), ""]
    s, n = metrics["sentiment"], metrics["n"]
    lines += [f"Sentiment: {pct(s['negative'] / n)} negative, {pct(s['mixed'] / n)} mixed, "
              f"{pct(s['positive'] / n)} positive.", ""]

    lines += ["## Priority ranking", "",
              "| # | Theme | Mentions | Share (95% interval) | Avg rating | Says leaving | Trend | Type | Confidence | Priority |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for t in themes:
        rating = "n/a" if t["avg_rating"] is None else f"{t['avg_rating']:.1f}"
        trend = "n/a" if t["trend"] is None else f"{t['trend'] * 100:+.0f} pts"
        priority = "–" if t["type"] == "Strength" else f"{t['priority']:.2f}"
        lines.append(f"| {t['rank']} | {t['name']} | {t['mentions']} | {pct(t['share'])} "
                     f"({pct(t['ci_low'])}–{pct(t['ci_high'])}) | {rating} | {pct(t['churn_share'])} | {trend} | "
                     f"{t['quadrant']} | {t['confidence']} | {priority} |")
    lines += ["", "Priority = share × impact × confidence ÷ effort. Impact comes from ratings and churn; "
              "effort is a judgment to validate with the team.", ""]

    lines += ["## Themes", ""]
    for t in themes:
        b = by_theme.get(t["id"], {})
        lines += [f"### {t['rank']}. {t['name']}", ""]
        for e in t["evidence"]:
            lines.append(f"- Evidence: “{e['quote']}” ({e['review_id']})")
        if b.get("root_cause_hypothesis"):
            lines.append(f"- Why (hypothesis): {b['root_cause_hypothesis']}")
        if b.get("business_impact"):
            lines.append(f"- Business impact: {b['business_impact']}")
        lines.append("")

    lines += ["## Recommendations", "", "| Theme | Action | Owner | KPI | Effort (validate) |", "|---|---|---|---|---|"]
    for t in themes:
        b = by_theme.get(t["id"], {})
        lines.append(f"| {t['name']} | {b.get('action', '')} | {b.get('owner', '')} | {b.get('kpi', '')} | "
                     f"{t['effort']}/5 |")
    lines.append("")

    churn = metrics["churn_ids"]
    lines += ["## Churn signals", "", f"{len(churn)} of {n} reviews ({pct(len(churn) / n)}) say the customer "
              "will leave, uninstall or switch." if n else "No reviews.", ""]
    if churn:
        lines += [f"Reviews: {', '.join(churn)}. The 'Says leaving' column shows which themes they sit in.", ""]

    lines += ["## Evaluation report", "", "| Check | Type | Result | Detail |", "|---|---|---|---|"]
    for e in evals:
        detail = e["detail"] if isinstance(e["detail"], str) else "; ".join(map(str, e["detail"]))
        result = "pass" if e["passed"] else ("FAIL" if e["type"] == "hard" else "below target")
        lines.append(f"| {e['check']} | {e['type']} | {result} | {detail} |")
    lines.append("")

    notes = [f"Removed {quality['empty']} empty, {quality['duplicates']} duplicate, "
             f"{quality['near_duplicates']} near-duplicate and {quality['too_short']} too-short rows.",
             f"Masked {quality['pii_masked']} emails or phone numbers."]
    if quality["dropped_columns"]:
        notes.append(f"Dropped personal columns: {', '.join(quality['dropped_columns'])}.")
    if quality["injection_flags"]:
        notes.append(f"Possible prompt injection in {', '.join(quality['injection_flags'])}; treated as data.")
    if not quality["has_rating"]:
        notes.append("No usable rating column: rating gap skipped, impact uses churn intent, confidence lowered one level.")
    if not quality["has_date"]:
        notes.append("No usable date column: trend skipped.")
    if label_report["dropped"]:
        notes.append(f"Excluded after {MAX_RETRIES} retries: {', '.join(label_report['dropped'])}.")
    if label_report["rejected_attempts"]:
        notes.append(f"Labels rejected by verification and redone: {label_report['rejected_attempts']}.")
    lines += ["## Data notes", ""] + [f"- {x}" for x in notes] + [""]
    if brief.get("follow_up_question"):
        lines += ["---", "", brief["follow_up_question"], ""]
    return "\n".join(lines)


def write_metrics_csv(path, metrics):
    cols = ["rank", "id", "name", "type", "mentions", "share", "ci_low", "ci_high", "avg_rating", "rating_gap",
            "churn_share", "trend", "impact", "effort", "confidence", "quadrant", "priority"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(metrics["themes"])


# ---------------------------------------------------------------- the run

def run(args):
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    model = get_model(args.model, args.model_name, faults=args.mock_faults, replay_dir=args.replay_dir)
    log = RunLog(run_dir / "run_log.jsonl", model)

    reviews, quality = load_reviews(args.data, args.min_reviews)
    save(run_dir / "quality_report.json", quality)
    log.write("1 load and clean", "ok", note=f"{quality['usable']} usable of {quality['raw_rows']}")

    codebook = get_codebook(model, reviews, args, run_dir, log)
    labels, label_report = label_all(model, reviews, codebook, args, log)
    save(run_dir / "labels.json", list(labels.values()))

    metrics = score(aggregate(reviews, labels, codebook, quality["has_rating"], quality["has_date"]),
                    quality["has_rating"])
    save(run_dir / "metrics.json", metrics)
    write_metrics_csv(run_dir / "metrics.csv", metrics)
    log.write("6 aggregate and score", "ok", note=f"{sum(t['mentions'] > 0 for t in metrics['themes'])} themes found")

    brief, hard, soft = write_and_check(model, metrics, args, log)
    save(run_dir / "brief.json", brief)

    by_id = {r["id"]: r for r in reviews}
    evals = build_eval(metrics, by_id, hard, soft, label_report, quality)
    verified = all(e["passed"] for e in evals if e["type"] == "hard")
    save(run_dir / "eval_report.json", {"verified": verified, "checks": evals, "labels": label_report})
    memo = render_memo(args, model, quality, metrics, brief, evals, label_report, run_id)
    (run_dir / "memo.md").write_text(memo, encoding="utf-8")
    log.write("9 deliver", "verified" if verified else "delivered with warnings", note=str(run_dir / "memo.md"))
    return {"run_dir": run_dir, "verified": verified, "metrics": metrics, "brief": brief, "evals": evals}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Turn raw customer reviews into a verified, prioritised brief.")
    p.add_argument("--data", required=True, help="CSV with at least an id and a text column")
    p.add_argument("--company", default="The client")
    p.add_argument("--question", default="What should we fix first to keep customers?")
    p.add_argument("--model", choices=["mock", "claude", "replay"], default="mock")
    p.add_argument("--replay-dir", default=None, help="Folder of recorded model responses (with --model replay)")
    p.add_argument("--model-name", default=None, help="Override the model name")
    p.add_argument("--auto-approve", action="store_true", help="Skip the human codebook check (demos only)")
    p.add_argument("--min-reviews", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--max-tokens", type=int, default=400_000, help="Token budget for the whole run")
    p.add_argument("--runs-dir", default="runs")
    p.add_argument("--mock-faults", action="store_true", help="Mock only: inject bad quotes to show the retry loop")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        result = run(args)
    except (QualityGateError, StopRun, ModelError) as exc:
        print(f"\nStopped: {exc}")
        return 2
    status = "all hard checks passed" if result["verified"] else "delivered with warnings"
    print(f"\n{result['brief'].get('headline', '')}\nMemo: {result['run_dir'] / 'memo.md'} ({status})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
