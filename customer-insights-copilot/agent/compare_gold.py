"""Human eval: compare the agent's labels with your own on a gold set.

1. Make a template of 50 reviews to label yourself:
     python compare_gold.py template --data sample_reviews.csv --out gold.csv
2. Open gold.csv and fill the `theme` column with the main theme id from the run's codebook.json.
3. Score the agent against you:
     python compare_gold.py score --gold gold.csv --labels runs/<run id>/labels.json
"""
import argparse
import csv
import json
import random
from collections import Counter

from tools import load_reviews


def make_template(data, out, k=50, seed=11):
    reviews, _ = load_reviews(data, min_reviews=1)
    picked = random.Random(seed).sample(reviews, min(k, len(reviews)))
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["review_id", "text", "theme"])
        for r in picked:
            writer.writerow([r["id"], r["text"], ""])
    print(f"Wrote {len(picked)} reviews to {out}. Fill the theme column, then run `score`.")


def kappa(pairs):
    """Cohen's kappa for two raters over categorical labels."""
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    gold, agent = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(gold[c] * agent[c] for c in set(gold) | set(agent)) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def score(gold_path, labels_path):
    with open(gold_path, newline="", encoding="utf-8-sig") as handle:
        gold = {row["review_id"]: row["theme"].strip() for row in csv.DictReader(handle) if row.get("theme", "").strip()}
    with open(labels_path, encoding="utf-8") as handle:
        agent = {lab["review_id"]: lab["themes"][0] for lab in json.load(handle)}
    pairs = [(gold[rid], agent[rid]) for rid in gold if rid in agent]
    if not pairs:
        print("No overlapping reviews. Check the review IDs in both files.")
        return
    agree = sum(a == b for a, b in pairs)
    k = kappa(pairs)
    print(f"Reviews compared: {len(pairs)}")
    print(f"Agreement on main theme: {agree}/{len(pairs)} ({agree / len(pairs):.0%})")
    print(f"Cohen's kappa: {k:.2f} ({'good' if k >= 0.6 else 'needs work'}; 0.6 or more is a common bar)")
    print("\nTheme                     You  Agent  Both")
    for theme in sorted({a for a, _ in pairs} | {b for _, b in pairs}):
        mine = sum(a == theme for a, _ in pairs)
        theirs = sum(b == theme for _, b in pairs)
        both = sum(a == b == theme for a, b in pairs)
        print(f"{theme:<25} {mine:>4} {theirs:>6} {both:>5}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("template")
    t.add_argument("--data", required=True)
    t.add_argument("--out", default="gold.csv")
    s = sub.add_parser("score")
    s.add_argument("--gold", required=True)
    s.add_argument("--labels", required=True)
    args = parser.parse_args()
    if args.command == "template":
        make_template(args.data, args.out)
    else:
        score(args.gold, args.labels)
