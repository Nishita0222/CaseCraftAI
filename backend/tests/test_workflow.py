"""Database + approval gating + export (no web server needed)."""
import json
import unittest
import zipfile

from tests import conftest  # noqa: F401
from tests.helpers import demo_run
from app import db
from app.exporter import build_export


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init_db()
        cls.state = demo_run()[0]
        cls.p = db.create_project("T", "Helios Freight", "", synthetic=True)
        run = db.create_run(cls.p["id"], [("a", "A")])
        db.create_approvals(cls.p["id"], run["id"], cls.state["approval_items"])
        cls.run_id = run["id"]
        cls.result = {k: cls.state[k] for k in ("evidence", "kpis", "privacy", "versions", "quotes", "assets")}

    def test_export_blocked_until_human_approves(self):
        ap = db.list_approvals(self.p["id"], self.run_id)
        with self.assertRaises(PermissionError):
            build_export(self.p, self.run_id, self.result, ap, "Reviewer")

    def test_reviewer_name_required(self):
        a = db.list_approvals(self.p["id"], self.run_id)[0]
        with self.assertRaises(ValueError):
            db.decide_approval(a["id"], "approved", "  ")

    def test_partial_approval_exports_only_approved_items(self):
        ap = db.list_approvals(self.p["id"], self.run_id)
        gate = next(a for a in ap if a["item_name"] == "gatekeeper")
        db.decide_approval(gate["id"], "approved", "Dana Reviewer", "ok")
        ap = db.list_approvals(self.p["id"], self.run_id)
        z, excluded = build_export(self.p, self.run_id, self.result, ap, "Dana Reviewer")
        names = zipfile.ZipFile(z).namelist()
        self.assertIn("case_studies/gatekeeper.md", names)
        self.assertNotIn("case_studies/buyer.md", names)
        self.assertTrue(any("buyer" in e for e in excluded))
        sources = json.loads(zipfile.ZipFile(z).read("evidence/sources_index.json"))
        self.assertTrue(all("text" not in s for s in sources))  # no raw evidence text leaves the system

    def test_quote_needs_its_own_approval(self):
        ap = db.list_approvals(self.p["id"], self.run_id)
        for a in ap:
            if a["item_type"] != "quote":
                db.decide_approval(a["id"], "approved", "Dana Reviewer")
        ap = db.list_approvals(self.p["id"], self.run_id)
        _, excluded = build_export(self.p, self.run_id, self.result, ap, "Dana Reviewer")
        self.assertTrue(any("quote" in e for e in excluded))

    def test_audit_trail(self):
        a = db.list_approvals(self.p["id"], self.run_id)[-1]
        db.decide_approval(a["id"], "rejected", "Dana Reviewer", "not yet")
        self.assertTrue(any(r["action"].startswith("approval_") for r in db.list_audit(self.p["id"])))
