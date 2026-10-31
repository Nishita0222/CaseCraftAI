import unittest
from pathlib import Path

from tests import conftest  # noqa: F401
from tests.helpers import demo_run
from app.extractors import extract_document
from app.text_utils import fmt_num, numbers_in, parse_number, split_sentences


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.files = {Path(f["path"]).name: Path(f["path"]) for f in demo_run()[2]}

    def test_pdf_text(self):
        chunks, _ = extract_document(self.files["statement_of_work.pdf"])
        self.assertIn("kick-off", " ".join(c["text"] for c in chunks))

    def test_docx_paragraphs_and_table(self):
        chunks, _ = extract_document(self.files["project_report.docx"])
        self.assertTrue(any(c.get("row") and c["row"].get("KPI") == "Support tickets per week" for c in chunks))

    def test_xlsx_rows_keep_headers(self):
        chunks, _ = extract_document(self.files["kpi_results.xlsx"])
        row = next(c for c in chunks if "Order processing" in c["text"])["row"]
        self.assertEqual(row["Baseline"], "48")

    def test_email_has_date_and_metadata(self):
        chunks, _ = extract_document(self.files["change_request.eml"])
        self.assertTrue(chunks[0]["metadata"])
        self.assertEqual(chunks[0]["date"], "2025-02-24")

    def test_text_utils(self):
        self.assertEqual(fmt_num(parse_number("1,200.50")), "1,200.5")
        self.assertEqual(len(split_sentences("Value was 4.2% today. Next one.")), 2)
        self.assertEqual(numbers_in("48 hours to 1,200"), {"48", "1200"})
