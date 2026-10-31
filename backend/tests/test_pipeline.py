import unittest
from decimal import Decimal

from tests import conftest  # noqa: F401
from tests.helpers import demo_run
from app.validators import validate_claim


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state, cls.steps, _, _ = demo_run()
        cls.kpis = {k["key"]: k for k in cls.state["kpis"]}

    def test_all_agents_ran(self):
        done = [a for a, s, _ in self.steps if s == "done"]
        self.assertEqual(len(done), 8)

    def test_kpi_calculation_is_recomputed(self):
        k = self.kpis["order processing time"]
        self.assertEqual(Decimal(k["pct_change"]), Decimal("75.0"))
        self.assertIn("(48 - 12) / 48", k["calc"])
        self.assertEqual(k["status"], "verified")
        self.assertGreaterEqual(len(k["refs"]), 2)  # corroborated by Excel + DOCX

    def test_conflict_resolved_by_authority(self):
        k = self.kpis["on-time delivery rate"]
        self.assertEqual(k["status"], "conflict_resolved")
        self.assertEqual(k["result"], "94")
        self.assertTrue(k["overridden"])

    def test_wrong_stated_percentage_is_flagged(self):
        k = self.kpis["picking error rate"]
        self.assertEqual(k["pct_change"], "73.8")
        self.assertTrue(any("80%" in w for w in k["warnings"]))

    def test_equal_authority_conflict_is_unresolved_and_excluded(self):
        k = self.kpis["warehouse space utilization"]
        self.assertEqual(k["status"], "unresolved")
        self.assertFalse(k["usable"])
        text = " ".join(v["markdown"] for v in self.state["versions"])
        self.assertNotIn("utilization", text.lower())

    def test_nda_blocks_kpi(self):
        k = self.kpis["freight cost saving"]
        self.assertTrue(k["privacy_blocked"])
        self.assertNotIn("1,900,000", " ".join(v["markdown"] for v in self.state["versions"]))

    def test_scope_changes_and_timeline(self):
        self.assertGreaterEqual(len(self.state["scope_changes"]), 1)
        dates = [t["date"] for t in self.state["timeline"]]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(self.state["span"]["days"], 158)

    def test_privacy_no_leaks(self):
        blob = " ".join(v["markdown"] for v in self.state["versions"]).lower()
        for banned in ("helios", "priya", "@", "555", "480,000"):
            self.assertNotIn(banned, blob)
        self.assertTrue(self.state["privacy"]["recheck"]["passed"])
        self.assertIn("E006", self.state["privacy"]["restricted_refs"])  # contract value sentence

    def test_three_versions_all_grounded_with_citations(self):
        self.assertEqual({v["key"] for v in self.state["versions"]}, {"gatekeeper", "user", "buyer"})
        for v in self.state["versions"]:
            self.assertTrue(v["grounding"]["ok"], v["grounding"]["issues"])
            self.assertEqual(v["status"], "ready_for_review")

    def test_quote_is_verbatim(self):
        q = self.state["quotes"][0]
        ev = {e["ref"]: e for e in self.state["evidence"]}
        self.assertIn(q["quote"], ev[q["ref"]]["text"])
        self.assertEqual(q["attribution"], "the client's operations lead")

    def test_at_least_three_assets_exist(self):
        from pathlib import Path
        self.assertGreaterEqual(len(self.state["assets"]), 3)
        for a in self.state["assets"]:
            self.assertTrue(Path(a["path"]).stat().st_size > 1000)
        self.assertTrue(Path(self.state["approval_pack"]["docx"]).exists())

    def test_human_approval_items_created(self):
        self.assertTrue(self.state["validation"]["human_approval_required"])
        types = {i["item_type"] for i in self.state["approval_items"]}
        self.assertEqual(types, {"version", "asset", "quote"})


class ValidatorTests(unittest.TestCase):
    def test_invented_number_is_rejected(self):
        ev = {"E001": {"text": "Order time fell from 48 hours to 12 hours.", "date": None}}
        bad = {"text": "Order time fell by 90%.", "refs": ["E001"], "type": "kpi"}
        self.assertTrue(validate_claim(bad, ev))
        good = {"text": "Order time fell from 48 hours to 12 hours.", "refs": ["E001"], "type": "kpi"}
        self.assertEqual(validate_claim(good, ev), [])

    def test_claim_without_citation_is_rejected(self):
        self.assertTrue(validate_claim({"text": "We are the best.", "refs": [], "type": "kpi"}, {}))

    def test_fake_quote_is_rejected(self):
        ev = {"E001": {"text": "She said, “It works well for us every single day.”", "date": None}}
        self.assertTrue(validate_claim({"text": "x", "refs": ["E001"], "type": "quote", "quote": "It is magic"}, ev))
