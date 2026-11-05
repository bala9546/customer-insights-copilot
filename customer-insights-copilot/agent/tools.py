"""Deterministic tools.

Everything that produces or checks a number lives here. The language model
labels text and writes prose; it never computes a figure.
"""
import csv
import difflib
import math
import random
import re
from datetime import date, timedelta

# Column names the loader recognises (case-insensitive). Only id and text are required.
ID_COLS = ("review_id", "id", "response_id", "ticket_id")
TEXT_COLS = ("text", "review", "comment", "content", "feedback", "body")
RATING_COLS = ("rating", "stars", "score")
DATE_COLS = ("date", "review_date", "created_at")
NAME_COLS = ("name", "user", "username", "user_name", "author", "reviewer", "reviewer_name")

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<![\w])\+?\d(?:[\s-]?\d){9,12}(?![\w])")
INJECTION = re.compile(
    r"ignore (all |any )?(the )?(previous|prior|above) instructions|system prompt|"
    r"you are now|disregard (the|your) (rules|instructions)",
    re.I,
)
MONEY = re.compile(r"revenue|profit|₹|\$|\binr\b|\brupees?\b|\blakhs?\b|\bcrores?\b", re.I)
HEDGE = re.compile(r"\b(likely|may|might|possibly|could|suggests?|appears?|probably)\b", re.I)
NUMBER = re.compile(r"\d+(?:\.\d+)?")

SENTIMENTS = {"negative", "mixed", "positive"}
CONF_WEIGHT = {"High": 1.0, "Medium": 0.8, "Low": 0.5}


class QualityGateError(Exception):
    """The data is not fit for analysis; the agent stops and asks the human."""


# ---------------------------------------------------------------- loading

def normalize(text):
    """Lower-case, straighten quotes and collapse whitespace, for comparisons only."""
    text = (text or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def _pick(headers, options):
    for option in options:
        if option in headers:
            return headers[option]
    return None


def _parse_rating(value):
    try:
        rating = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None


def _parse_date(value):
    value = str(value or "").strip()
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        y, m, d = map(int, match.groups())
    else:
        match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", value)
        if not match:
            return None
        d, m, y = map(int, match.groups())
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def mask_pii(text):
    """Mask emails and phone-like numbers. Returns (masked_text, number_of_masks)."""
    text, n_email = EMAIL.subn("[EMAIL]", text)
    text, n_phone = PHONE.subn("[PHONE]", text)
    return text, n_email + n_phone


def load_reviews(path, min_reviews=30):
    """Read a CSV, detect columns, clean the rows and run the data-quality gate.

    Returns (reviews, report). Each review is {"id", "text", "rating", "date"}.
    Raises QualityGateError when the data is not fit for analysis.
    """
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}
        rows = list(reader)

    id_col, text_col = _pick(headers, ID_COLS), _pick(headers, TEXT_COLS)
    if not text_col:
        raise QualityGateError(f"No text column found. Name one of: {', '.join(TEXT_COLS)}.")
    rating_col, date_col = _pick(headers, RATING_COLS), _pick(headers, DATE_COLS)
    dropped_cols = [headers[c] for c in NAME_COLS if c in headers]

    report = {
        "raw_rows": len(rows), "empty": 0, "duplicates": 0, "near_duplicates": 0,
        "too_short": 0, "pii_masked": 0, "injection_flags": [],
        "columns": {"id": id_col, "text": text_col, "rating": rating_col, "date": date_col},
        "dropped_columns": dropped_cols,
    }

    reviews, seen = [], set()
    for i, row in enumerate(rows, start=1):
        raw = (row.get(text_col) or "").strip()
        if not raw:
            report["empty"] += 1
            continue
        key = normalize(raw)
        # Short reviews first: repeated one-word reviews ("good") are normal, not a broken export,
        # so they must not count towards the duplicate gate below.
        if len(key.split()) < 3:
            report["too_short"] += 1
            continue
        if key in seen:
            report["duplicates"] += 1
            continue
        seen.add(key)
        text, masks = mask_pii(raw)
        report["pii_masked"] += masks
        rid = (row.get(id_col) or "").strip() if id_col else ""
        rid = rid or f"R{i:04d}"
        if INJECTION.search(text):
            report["injection_flags"].append(rid)
        reviews.append({
            "id": rid,
            "text": text,
            "rating": _parse_rating(row.get(rating_col)) if rating_col else None,
            "date": _parse_date(row.get(date_col)) if date_col else None,
        })

    # Near-duplicates (copy-paste spam, bot reviews): keep the first, drop the rest.
    kept = []
    for review in reviews:
        key = normalize(review["text"])
        is_copy = False
        for other in kept:
            matcher = difflib.SequenceMatcher(None, key, normalize(other["text"]))
            if matcher.real_quick_ratio() >= 0.92 and matcher.ratio() >= 0.92:
                is_copy = True
                break
        if is_copy:
            report["near_duplicates"] += 1
        else:
            kept.append(review)
    reviews = kept

    ids = [r["id"] for r in reviews]
    if len(ids) != len(set(ids)):
        raise QualityGateError("Review IDs are not unique. Fix the id column and try again.")

    n = len(reviews)
    report["usable"] = n
    report["has_rating"] = n > 0 and sum(r["rating"] is not None for r in reviews) >= 0.8 * n
    report["has_date"] = n > 0 and sum(r["date"] is not None for r in reviews) >= 0.8 * n
    dated = sorted(r["date"] for r in reviews if r["date"])
    report["date_range"] = [dated[0], dated[-1]] if dated else None

    if n < min_reviews:
        raise QualityGateError(
            f"Only {n} usable reviews after cleaning (minimum {min_reviews}). Add more data."
        )
    if report["raw_rows"] and (report["duplicates"] + report["near_duplicates"]) / report["raw_rows"] > 0.30:
        raise QualityGateError("More than 30% of rows are duplicates. Check the export before analysing it.")
    return reviews, report


def sample_reviews(reviews, k=30, seed=7):
    """A fixed, reproducible sample for proposing the codebook."""
    rng = random.Random(seed)
    return rng.sample(reviews, min(k, len(reviews)))


# ---------------------------------------------------------------- codebook

def validate_codebook(data):
    """Check the proposed themes and return a clean codebook with 'other' added."""
    themes, seen = [], set()
    for theme in (data or {}).get("themes", []):
        tid = re.sub(r"[^a-z0-9_]", "_", str(theme.get("id", "")).strip().lower()).strip("_")
        if not tid or tid in seen or tid == "other":
            continue
        try:
            effort = int(theme.get("effort", 3))
        except (TypeError, ValueError):
            effort = 3
        seen.add(tid)
        themes.append({
            "id": tid,
            "name": str(theme.get("name") or tid.replace("_", " ").title()).strip(),
            "definition": str(theme.get("definition", "")).strip(),
            "effort": min(5, max(1, effort)),
            "effort_reason": str(theme.get("effort_reason", "")).strip(),
        })
    if not 3 <= len(themes) <= 10:
        raise ValueError(f"Codebook needs 3 to 10 themes, got {len(themes)}.")
    themes.append({"id": "other", "name": "Other", "definition": "Fits no theme above.",
                   "effort": 3, "effort_reason": ""})
    return {"themes": themes}


# ---------------------------------------------------------------- verification

def verify_label(label, reviews_by_id, theme_ids):
    """Return a list of problems with one label; an empty list means it passed."""
    problems = []
    rid = label.get("review_id")
    if rid not in reviews_by_id:
        return [f"unknown review_id {rid!r}"]
    themes = label.get("themes")
    if not isinstance(themes, list) or not themes:
        problems.append("themes must be a non-empty list")
    else:
        bad = [t for t in themes if t not in theme_ids]
        if bad:
            problems.append(f"themes not in codebook: {bad}")
    if label.get("sentiment") not in SENTIMENTS:
        problems.append("sentiment must be negative, mixed or positive")
    if not isinstance(label.get("churn_intent"), bool):
        problems.append("churn_intent must be true or false")
    evidence = str(label.get("evidence") or "")
    if len(normalize(evidence)) < 3:
        problems.append("evidence is missing")
    elif normalize(evidence) not in normalize(reviews_by_id[rid]["text"]):
        problems.append("evidence is not a word-for-word quote from the review")
    elif len(evidence.split()) > 30:
        problems.append("evidence is longer than 30 words")
    return problems


# ---------------------------------------------------------------- metrics

def wilson(k, n, z=1.96):
    """95% Wilson score interval for a share of k out of n."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _trend(theme_ids_by_review, reviews, theme_id):
    """Share in the last 30 days minus share in the 30 days before (None if too few)."""
    dated = [r for r in reviews if r["date"]]
    if not dated:
        return None
    end = date.fromisoformat(max(r["date"] for r in dated))
    recent_start, prior_start = end - timedelta(days=29), end - timedelta(days=59)
    recent = [r for r in dated if date.fromisoformat(r["date"]) >= recent_start]
    prior = [r for r in dated if prior_start <= date.fromisoformat(r["date"]) < recent_start]
    if len(recent) < 10 or len(prior) < 10:
        return None
    share = lambda group: sum(theme_id in theme_ids_by_review[r["id"]] for r in group) / len(group)
    return share(recent) - share(prior)


def aggregate(reviews, labels, codebook, has_rating, has_date):
    """Compute every number the memo shows. `labels` maps review_id -> verified label."""
    labelled = [r for r in reviews if r["id"] in labels]
    n = len(labelled)
    themes_of = {r["id"]: set(labels[r["id"]]["themes"]) for r in labelled}
    overall_rating = _mean([r["rating"] for r in labelled]) if has_rating else None
    sentiment = {s: sum(labels[r["id"]]["sentiment"] == s for r in labelled) for s in sorted(SENTIMENTS)}
    churn_ids = [r["id"] for r in labelled if labels[r["id"]]["churn_intent"]]

    themes = []
    for theme in codebook["themes"]:
        if theme["id"] == "other":
            continue
        members = [r for r in labelled if theme["id"] in themes_of[r["id"]]]
        k = len(members)
        low, high = wilson(k, n)
        avg = _mean([r["rating"] for r in members]) if has_rating else None
        churn_k = sum(labels[r["id"]]["churn_intent"] for r in members)
        votes = [labels[r["id"]]["sentiment"] for r in members]
        positive = bool(votes) and votes.count("positive") > len(votes) / 2
        # Evidence: prefer reviews where this is the main theme, then churn intent, then the most
        # telling rating (lowest for issues, highest for strengths).
        sign = -1 if positive else 1
        ordered = sorted(members, key=lambda r: (labels[r["id"]]["themes"][0] != theme["id"],
                                                 not labels[r["id"]]["churn_intent"],
                                                 sign * (r["rating"] if r["rating"] is not None else 3)))
        themes.append({
            "id": theme["id"], "name": theme["name"], "mentions": k,
            "share": k / n if n else 0.0, "ci_low": low, "ci_high": high,
            "avg_rating": avg,
            "rating_gap": (avg - overall_rating) if (avg is not None and overall_rating is not None) else None,
            "churn_mentions": churn_k, "churn_share": churn_k / k if k else 0.0,
            "trend": _trend(themes_of, labelled, theme["id"]) if has_date else None,
            "type": "Strength" if positive else "Issue",
            "review_ids": [r["id"] for r in members],
            "evidence": [{"review_id": r["id"], "quote": labels[r["id"]]["evidence"]} for r in ordered[:2]],
            "effort": theme["effort"], "effort_reason": theme.get("effort_reason", ""),
        })

    other_k = sum(themes_of[r["id"]] == {"other"} for r in labelled)
    return {
        "n": n, "overall_rating": overall_rating, "sentiment": sentiment,
        "churn_ids": churn_ids, "themes": themes,
        "other_share": other_k / n if n else 0.0,
        "coverage": (n - other_k) / n if n else 0.0,
    }


def impact_score(avg_rating, churn_share):
    """Impact 1-5 from the data. Starting thresholds; tune them on your own data."""
    if avg_rating is None:  # no rating column: fall back to churn intent only
        if churn_share >= 0.30:
            return 5
        if churn_share >= 0.15:
            return 4
        return 3 if churn_share >= 0.05 else 2
    if avg_rating <= 1.5 or churn_share >= 0.30:
        return 5
    if avg_rating <= 2.5 or churn_share >= 0.15:
        return 4
    if avg_rating <= 3.5:
        return 3
    if avg_rating <= 4.2:
        return 2
    return 1


def confidence(mentions, ci_low, ci_high, has_rating):
    level = "High" if mentions >= 10 and (ci_high - ci_low) <= 0.20 else "Medium" if mentions >= 3 else "Low"
    if not has_rating:  # severity is not measured, so trust drops one level
        level = {"High": "Medium", "Medium": "Low", "Low": "Low"}[level]
    return level


def quadrant(impact, effort):
    if impact >= 4 and effort <= 2:
        return "Quick win"
    if impact >= 4:
        return "Major project"
    if effort <= 2:
        return "Fill-in"
    return "Deprioritize"


def score(metrics, has_rating):
    """Add impact, confidence and a RICE-style priority to each theme, and rank them."""
    for t in metrics["themes"]:
        t["impact"] = impact_score(t["avg_rating"], t["churn_share"])
        t["confidence"] = confidence(t["mentions"], t["ci_low"], t["ci_high"], has_rating)
        t["priority"] = t["share"] * t["impact"] * CONF_WEIGHT[t["confidence"]] / t["effort"]
        t["quadrant"] = "Strength" if t["type"] == "Strength" else quadrant(t["impact"], t["effort"])
    metrics["themes"].sort(key=lambda t: (t["type"] == "Strength", t["mentions"] == 0, -t["priority"]))
    for rank, t in enumerate(metrics["themes"], start=1):
        t["rank"] = rank
    return metrics


# ---------------------------------------------------------------- brief checks

def brief_text_fields(brief):
    fields = [brief.get("headline", ""), brief.get("summary", ""), brief.get("follow_up_question", "")]
    for t in brief.get("themes", []):
        fields += [t.get(k, "") for k in ("root_cause_hypothesis", "business_impact", "action", "owner", "kpi")]
    return [str(f or "") for f in fields]


def check_brief(brief, metrics, allowed_numbers=()):
    """Hard checks must all pass; soft checks are reported. Returns (hard, soft) problem lists."""
    hard, soft = [], []
    if not str(brief.get("headline", "")).strip():
        hard.append("headline is empty")
    text = " ".join(brief_text_fields(brief))
    allowed = {str(a) for a in allowed_numbers}
    stray = sorted({x for x in NUMBER.findall(text) if x not in allowed})
    if stray:
        hard.append(f"numbers written by the model (only code may write numbers): {stray}")
    money = sorted({m.group(0) for m in MONEY.finditer(text)})
    if money:
        hard.append(f"financial claims not supported by the data: {money}")
    known = {t["id"] for t in metrics["themes"] if t["mentions"]}
    given = {t.get("id") for t in brief.get("themes", [])}
    invented = sorted(x for x in given - known if x)
    if invented:
        hard.append(f"themes not in the data: {invented}")
    for t in brief.get("themes", []):
        missing = [k for k in ("action", "owner", "kpi") if not str(t.get(k, "")).strip()]
        if missing:
            hard.append(f"{t.get('id')}: missing {', '.join(missing)}")
        hypothesis = str(t.get("root_cause_hypothesis", ""))
        if hypothesis and not HEDGE.search(hypothesis):
            soft.append(f"{t.get('id')}: root cause is not worded as a hypothesis")
    issues = {t["id"] for t in metrics["themes"] if t["type"] == "Issue" and t["mentions"]}
    uncovered = sorted(issues - given)
    if uncovered:
        hard.append(f"no recommendation for: {uncovered}")
    return hard, soft


def unverified_quotes(metrics, reviews_by_id):
    """Re-check every quote the memo will show against its review."""
    bad = []
    for t in metrics["themes"]:
        for e in t["evidence"]:
            review = reviews_by_id.get(e["review_id"])
            if not review or normalize(e["quote"]) not in normalize(review["text"]):
                bad.append(e["review_id"])
    return bad
