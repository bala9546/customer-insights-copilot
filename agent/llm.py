"""Model layer: Claude, a replay of recorded responses, or an offline mock, all with the same interface.

Every model exposes complete_json(task, system, prompt, context) -> dict.
Claude reads only `system` and `prompt`; the mock and replay read `context`, so the
whole pipeline can run without an API key.
"""
import json
import os
import re
import time
from pathlib import Path


class ModelError(Exception):
    pass


def parse_json(text):
    """Pull the JSON object out of a model reply, tolerating code fences."""
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ModelError("The model did not return JSON.")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ModelError(f"The model returned invalid JSON: {exc}") from exc


class _RealModel:
    retries = 5

    def __init__(self):
        self.tokens_used = 0

    def complete_json(self, task, system, prompt, context=None):
        last = None
        for attempt in range(self.retries):
            try:
                text, tokens = self._call(system, prompt)
                self.tokens_used += tokens
                return parse_json(text)
            except ModelError as exc:  # bad JSON: ask again
                last = exc
            except Exception as exc:  # rate limit (429), busy (503) or network: wait longer each time
                last = exc
                if attempt < self.retries - 1:
                    wait = min(60, 10 * 2 ** attempt)  # 10, 20, 40, 60 seconds
                    print(f"  model busy or rate-limited, retrying in {wait}s ({str(exc)[:60]})")
                    time.sleep(wait)
        raise ModelError(f"{task} failed after {self.retries} attempts: {last}")


class ClaudeModel(_RealModel):
    def __init__(self, model=None):
        super().__init__()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ModelError("Set ANTHROPIC_API_KEY.")
        import anthropic  # pip install anthropic
        self.client = anthropic.Anthropic()
        self.name = model or os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

    def _call(self, system, prompt):
        # No temperature: the current Messages API reference does not list it for current models.
        message = self.client.messages.create(
            model=self.name, max_tokens=8000, system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
        return text, message.usage.input_tokens + message.usage.output_tokens



# ---------------------------------------------------------------- replay

class ReplayModel:
    """Replays model responses recorded in a folder, through the same harness.

    The folder holds codebook.json, labels.json and brief.json (the model's three
    outputs) and an optional source.txt naming who produced them. Every check,
    count and score is still computed by the agent's code, so a replay is a full,
    reproducible run.
    """

    def __init__(self, folder):
        self.folder, self.tokens_used, self._labels = Path(folder), 0, None
        source = self.folder / "source.txt"
        self.name = source.read_text(encoding="utf-8").strip() if source.exists() else f"replay of {folder}"

    def _load(self, filename):
        path = self.folder / filename
        if not path.exists():
            raise ModelError(f"Replay file missing: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def complete_json(self, task, system, prompt, context=None):
        if task == "propose_codebook":
            return self._load("codebook.json")
        if task == "label_batch":
            if self._labels is None:
                data = self._load("labels.json")
                items = data["labels"] if isinstance(data, dict) else data
                self._labels = {label["review_id"]: label for label in items}
            return {"labels": [self._labels[r["id"]] for r in context["batch"] if r["id"] in self._labels]}
        if task == "write_brief":
            return self._load("brief.json")
        raise ModelError(f"Replay has no task {task!r}")

# ---------------------------------------------------------------- offline mock

MOCK_THEMES = [
    ("payments_checkout", "Payment and checkout failures",
     "Payments, coupons or checkout steps that fail, double-charge or block an order; not pricing complaints.",
     2, "Usually one broken flow; a hotfix is possible.",
     ["payment", "checkout", "coupon", "debited", "charged twice", "double charged", "transaction"]),
    ("delivery_speed", "Late or slow delivery",
     "Orders that arrive late, cold or after the time shown; not app speed.",
     4, "Needs courier capacity and estimate changes across operations.",
     ["late", "delay", "delayed", "hour", "cold", "waiting", "delivery time", "estimate"]),
    ("support", "Unhelpful customer support",
     "Slow, scripted or unresolved support, including refunds; not the original problem.",
     3, "Needs staffing and an escalation process.",
     ["support", "customer care", "bot", "refund", "agent", "complaint", "helpline"]),
    ("signup_login", "Sign-up and login problems",
     "OTP, registration or login steps that fail; not payment verification.",
     2, "Often fixable with a backup SMS provider.",
     ["otp", "login", "log in", "sign up", "signup", "register", "password"]),
    ("pricing_fees", "Fees and pricing",
     "Delivery fees, surge fees or prices seen as unfair; not failed payments.",
     4, "Pricing changes need commercial sign-off.",
     ["fee", "fees", "price", "prices", "expensive", "surge", "costly", "overpriced", "cheaper"]),
    ("app_bugs", "App crashes and bugs",
     "The app crashes, freezes or shows errors; not slow delivery.",
     3, "Needs debugging across devices and releases.",
     ["crash", "crashes", "crashed", "bug", "freezes", "hangs", "lag", "not loading", "error"]),
    ("praise", "What customers like",
     "Positive comments on variety, ease of use, speed or staff.",
     1, "Keep doing what works.",
     ["love", "great", "excellent", "easy to use", "polite", "smooth", "best", "amazing", "quick delivery"]),
]
CHURN_WORDS = ["uninstall", "uninstalled", "uninstalling", "never again", "never ordering",
               "switching to", "switched to", "moving to", "deleting the app", "last order"]
STAGES = {"payments_checkout": "Checkout", "delivery_speed": "Delivery", "support": "Support",
          "signup_login": "Sign-up", "pricing_fees": "Pricing", "app_bugs": "App use", "praise": None}
MOCK_BRIEF = {
    "payments_checkout": ("A recent release likely broke the coupon or payment step.",
                          "Lost orders at the last step and a risk to payment trust.",
                          "Hotfix the coupon and payment flow and add duplicate-charge protection.",
                          "Payments engineering", "Checkout success rate"),
    "delivery_speed": ("Delivery estimates may be too optimistic, and courier supply may fall short at peak hours.",
                       "Late food erodes repeat ordering.",
                       "Recalibrate delivery estimates and send live updates when an order runs late.",
                       "Delivery operations", "On-time delivery rate"),
    "support": ("Support is likely understaffed for escalations, with a bot that has no route to a person.",
                "Unresolved problems turn a single bad order into a lost customer.",
                "Add a human escalation path and a clear refund rule for missing items.",
                "Customer support", "First-contact resolution rate"),
    "signup_login": ("One-time passwords may depend on a single SMS provider with delivery gaps.",
                     "New customers give up before their first order.",
                     "Add a backup SMS provider and a resend option.",
                     "Growth engineering", "Sign-up completion rate"),
    "pricing_fees": ("Fees may not be explained clearly, so the app compares badly with rivals.",
                     "Price-sensitive customers may move to cheaper apps.",
                     "Test clearer fee breakdowns and a free-delivery threshold.",
                     "Pricing and product", "Repeat order rate"),
    "app_bugs": ("Recent releases may lack testing on older devices.",
                 "Crashes interrupt ordering and damage ratings.",
                 "Add crash monitoring and a release check on older devices.",
                 "App engineering", "Crash-free session rate"),
    "praise": ("Variety and ease of use likely keep loyal customers coming back.",
               "These strengths support retention while issues are fixed.",
               "Protect these strengths and feature them in marketing.",
               "Marketing", "Share of positive reviews"),
}


def _find(text, words):
    lower = text.lower()
    hits = [m.start() for w in words for m in [re.search(r"\b" + re.escape(w) + r"\b", lower)] if m]
    return min(hits) if hits else None


class MockModel:
    """Deterministic keyword-based stand-in for a real model.

    faults=True makes the first labelling pass paraphrase some evidence, so the
    verify-and-retry loop can be seen working.
    """

    name = "mock (offline, keyword rules)"

    def __init__(self, faults=False):
        self.tokens_used = 0
        self.faults = faults
        self._faulted = set()

    def complete_json(self, task, system, prompt, context=None):
        context = context or {}
        if task == "propose_codebook":
            return {"themes": [{"id": i, "name": n, "definition": d, "effort": e, "effort_reason": r}
                               for i, n, d, e, r, _ in MOCK_THEMES]}
        if task == "label_batch":
            return {"labels": [self._label(r, context["codebook"]) for r in context["batch"]]}
        if task == "write_brief":
            return self._brief(context["facts"])
        raise ModelError(f"Mock has no task {task!r}")

    def _label(self, review, codebook):
        text, ids = review["text"], {t["id"] for t in codebook["themes"]}
        found = sorted((pos, tid) for tid, *_, words in MOCK_THEMES
                       if tid in ids for pos in [_find(text, words)] if pos is not None)
        themes = [tid for _, tid in found][:3] or ["other"]
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        anchor = found[0][0] if found else 0
        offset, evidence = 0, sentences[0]
        for sentence in sentences:
            start = text.find(sentence, offset)
            if start <= anchor < start + len(sentence) + 1:
                evidence = sentence
                break
            offset = start + len(sentence)
        evidence = " ".join(evidence.split()[:25])
        if self.faults and review["id"] not in self._faulted and sum(map(ord, review["id"])) % 7 == 0:
            self._faulted.add(review["id"])
            evidence = "The customer says that " + evidence.lower()  # a paraphrase: verification must catch it
        rating = review.get("rating")
        if rating is not None:
            sentiment = "negative" if rating <= 2 else "mixed" if rating < 4 else "positive"
        else:
            pos = "praise" in themes
            neg = any(t not in ("praise", "other") for t in themes)
            sentiment = "mixed" if pos and neg else "positive" if pos else "negative"
        return {"review_id": review["id"], "themes": themes, "sentiment": sentiment,
                "journey_stage": STAGES.get(themes[0]), "churn_intent": _find(text, CHURN_WORDS) is not None,
                "evidence": evidence}

    def _brief(self, facts):
        issues = [f for f in facts if f["type"] == "Issue"]
        top = issues[0] if issues else facts[0]
        quick = next((f for f in issues if f["quadrant"] == "Quick win" and f is not top), None)
        headline = f"The biggest reason customers are unhappy is {top['name'].lower()}"
        headline += f", and the fastest extra win is fixing {quick['name'].lower()}." if quick else "."
        names = ", ".join(f["name"].lower() for f in issues[:3])
        summary = (f"The top issues are {names}. The ranking weighs how widespread each issue is, "
                   "how unhappy those customers are, and how hard it is to fix.")
        themes = []
        for f in facts:
            hyp, imp, act, own, kpi = MOCK_BRIEF.get(f["id"], ("The cause may need more research.",
                                                                 "Unclear from this sample.", "Investigate further.",
                                                                 "Product", "Theme share in new reviews"))
            themes.append({"id": f["id"], "root_cause_hypothesis": hyp, "business_impact": imp,
                           "action": act, "owner": own, "kpi": kpi})
        return {"headline": headline, "summary": summary, "themes": themes,
                "follow_up_question": f"Should I dig into the reviews behind {top['name'].lower()}, "
                                      "or turn these actions into a one-page plan?"}


def get_model(kind, model_name=None, faults=False, replay_dir=None):
    if kind == "mock":
        return MockModel(faults=faults)
    if kind == "claude":
        return ClaudeModel(model_name)
    if kind == "replay":
        if not replay_dir:
            raise ModelError("--model replay needs --replay-dir pointing at recorded responses.")
        return ReplayModel(replay_dir)
    raise ModelError(f"Unknown model {kind!r}: use mock, claude or replay.")
