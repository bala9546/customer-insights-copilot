"""Run from the agent folder:  python -m unittest discover tests"""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import agent  # noqa: E402
from tools import (QualityGateError, check_brief, confidence, impact_score, load_reviews,  # noqa: E402
                   mask_pii, quadrant, verify_label, wilson)

SAMPLE = HERE / "sample_reviews.csv"


class ToolTests(unittest.TestCase):
    def test_wilson_interval(self):
        low, high = wilson(3, 16)
        self.assertEqual((round(low * 100), round(high * 100)), (7, 43))
        low, high = wilson(38, 200)
        self.assertEqual((round(low * 100), round(high * 100)), (14, 25))

    def test_mask_pii(self):
        text, n = mask_pii("Call 9876543210 or mail me at a.b@example.com")
        self.assertEqual(n, 2)
        self.assertNotIn("9876543210", text)
        self.assertIn("[EMAIL]", text)

    def test_verify_label(self):
        reviews = {"R1": {"id": "R1", "text": "The app crashes at checkout. Uninstalling."}}
        themes = {"app_bugs", "other"}
        good = {"review_id": "R1", "themes": ["app_bugs"], "sentiment": "negative",
                "churn_intent": True, "evidence": "the app crashes at checkout"}
        self.assertEqual(verify_label(good, reviews, themes), [])
        paraphrase = dict(good, evidence="The app keeps crashing")
        self.assertTrue(verify_label(paraphrase, reviews, themes))
        invented_theme = dict(good, themes=["delivery"])
        self.assertTrue(verify_label(invented_theme, reviews, themes))
        self.assertTrue(verify_label(dict(good, review_id="R9"), reviews, themes))

    def test_check_brief(self):
        metrics = {"themes": [{"id": "app_bugs", "mentions": 4, "type": "Issue"}]}
        clean = {"headline": "Crashes drive churn.", "summary": "",
                 "themes": [{"id": "app_bugs", "root_cause_hypothesis": "Releases may lack testing.",
                             "business_impact": "Lost orders.", "action": "Add crash monitoring.",
                             "owner": "App engineering", "kpi": "Crash-free sessions"}]}
        self.assertEqual(check_brief(clean, metrics), ([], []))
        with_number = json.loads(json.dumps(clean))
        with_number["headline"] = "Crashes hit 40% of users."
        self.assertTrue(check_brief(with_number, metrics)[0])
        with_money = json.loads(json.dumps(clean))
        with_money["themes"][0]["business_impact"] = "Costs us revenue."
        self.assertTrue(check_brief(with_money, metrics)[0])
        no_owner = json.loads(json.dumps(clean))
        no_owner["themes"][0]["owner"] = ""
        self.assertTrue(check_brief(no_owner, metrics)[0])

    def test_scoring_rules(self):
        self.assertEqual(impact_score(1.4, 0.0), 5)
        self.assertEqual(impact_score(None, 0.2), 4)
        self.assertEqual(confidence(12, 0.20, 0.35, True), "High")
        self.assertEqual(confidence(12, 0.20, 0.35, False), "Medium")
        self.assertEqual(quadrant(5, 2), "Quick win")

    def test_quality_gate_stops_small_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "small.csv"
            path.write_text("id,text\n1,The app is slow today\n2,Payment failed again today\n", encoding="utf-8")
            with self.assertRaises(QualityGateError):
                load_reviews(path)

    def test_cleaning_on_sample(self):
        reviews, report = load_reviews(SAMPLE)
        self.assertEqual(report["raw_rows"], 47)
        self.assertEqual((report["duplicates"], report["near_duplicates"], report["too_short"]), (1, 1, 1))
        self.assertEqual(report["usable"], 44)
        self.assertIn("R037", report["injection_flags"])
        self.assertEqual(report["pii_masked"], 1)
        self.assertEqual(report["dropped_columns"], ["user_name"])


class EndToEndTests(unittest.TestCase):
    def run_agent(self, data, tmp, *extra):
        args = agent.parse_args(["--data", str(data), "--company", "FreshBite", "--model", "mock",
                                 "--auto-approve", "--runs-dir", tmp, *extra])
        return agent.run(args)

    def test_mock_run_with_faults(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_agent(SAMPLE, tmp, "--mock-faults")
            self.assertTrue(result["verified"])
            report = json.loads((result["run_dir"] / "eval_report.json").read_text(encoding="utf-8"))
            self.assertGreater(report["labels"]["rejected_attempts"], 0)  # the retry loop ran
            self.assertEqual(report["labels"]["dropped"], [])
            top = result["metrics"]["themes"][0]
            self.assertEqual(top["id"], "payments_checkout")
            self.assertGreater(top["trend"], 0)
            memo = (result["run_dir"] / "memo.md").read_text(encoding="utf-8")
            self.assertIn("Directional only", memo)
            self.assertNotIn("9876543210", memo)

    def test_text_only_data_degrades_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            text_only = Path(tmp) / "text_only.csv"
            with open(SAMPLE, newline="", encoding="utf-8") as src, open(text_only, "w", newline="", encoding="utf-8") as dst:
                writer = csv.writer(dst)
                writer.writerow(["id", "comment"])
                for row in csv.DictReader(src):
                    writer.writerow([row["review_id"], row["text"]])
            result = self.run_agent(text_only, tmp)
            self.assertTrue(result["verified"])
            self.assertTrue(all(t["avg_rating"] is None and t["trend"] is None for t in result["metrics"]["themes"]))
            memo = (result["run_dir"] / "memo.md").read_text(encoding="utf-8")
            self.assertIn("No usable rating column", memo)
            self.assertNotIn("| High |", memo)  # confidence is lowered without ratings


if __name__ == "__main__":
    unittest.main()
