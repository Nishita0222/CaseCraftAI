"""SYNTHETIC demo documents. Every name, number and quote here is invented for demonstration only."""
from email.message import EmailMessage
from pathlib import Path

CLIENT = "Helios Freight"
PROJECT = "Warehouse Visibility Platform (SYNTHETIC DEMO)"


def _eml(path, sender, subject, date, body):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Date"] = sender, "Delivery Lead <delivery.lead@northwind.example>", subject, date
    m.set_content(body, charset="utf-8")
    path.write_bytes(m.as_bytes())


def generate_demo_files(dest: Path) -> list:
    dest.mkdir(parents=True, exist_ok=True)
    files = []

    # 1. Statement of work (PDF)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    st = getSampleStyleSheet()["Normal"]
    lines = [
        "Statement of Work - Warehouse Visibility Platform (SYNTHETIC DEMO DATA).",
        "The objective of this engagement is to give Helios Freight a real-time order visibility dashboard for its regional warehouse.",
        "Project kick-off took place on 2025-01-13.",
        "Phase 1 discovery was completed on 2025-02-07.",
        "Confidentiality: This agreement is confidential and Helios Freight must not be named in any public material without written consent.",
        "The contract value of $480,000 must not be disclosed.",
        "Cost savings figures are confidential and must not be published.",
    ]
    p = dest / "statement_of_work.pdf"
    SimpleDocTemplate(str(p), pagesize=A4).build([x for l in lines for x in (Paragraph(l, st), Spacer(1, 8))])
    files.append(p)

    # 2. Project report (DOCX with narrative + KPI table)
    from docx import Document
    d = Document()
    d.add_heading("Project Status Report - Final (SYNTHETIC DEMO DATA)", 1)
    for t in [
        "The pilot go-live occurred on 12 March 2025 at the main warehouse.",
        "The platform was rolled out to all three warehouse zones on 28 April 2025.",
        "Final acceptance was signed on 20 June 2025.",
        "The delivery team reduced the average order processing time from 48 hours to 12 hours.",
        "The delivery team reduced the picking error rate from 4.2% to 1.1% by 80%.",
        "The delivery team improved the on-time delivery rate from 82% to 91%.",
    ]:
        d.add_paragraph(t)
    tbl = d.add_table(rows=2, cols=4)
    for i, h in enumerate(["KPI", "Baseline", "Result", "Status"]):
        tbl.rows[0].cells[i].text = h
    for i, v in enumerate(["Support tickets per week", "310", "205", "Final"]):
        tbl.rows[1].cells[i].text = v
    p = dest / "project_report.docx"
    d.save(str(p))
    files.append(p)

    # 3. KPI workbook (XLSX)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "KPIs"
    ws.append(["KPI", "Unit", "Baseline", "Result", "Target", "Status"])
    for r in [("Order processing time", "hours", 48, 12, 24, "Final"), ("Picking error rate", "%", 4.2, 1.1, 2.0, "Final"),
              ("On-time delivery rate", "%", 82, 94, 90, "Final"), ("Freight cost savings", "$", 1900000, 1450000, 1500000, "Final")]:
        ws.append(list(r))
    p = dest / "kpi_results.xlsx"
    wb.save(str(p))
    files.append(p)

    # 4-7. Emails
    p = dest / "change_request.eml"
    _eml(p, "Priya Nair <priya.nair@heliosfreight.example>", "Change request CR-007", "Mon, 24 Feb 2025 10:15:00 +0000",
         "Hi team,\n\nWe would like to raise change request CR-007 to add returns tracking to the scope. "
         "This is an additional requirement beyond the original statement of work.\n\n"
         "The revised scope was approved on 3 March 2025.\n\nRegards,\nPriya Nair\nPhone: +1 555 010 0199\n"
         "priya.nair@heliosfreight.example\n")
    files.append(p)
    p = dest / "utilization_update_a.eml"
    _eml(p, "Ops Analyst <ops.analyst@northwind.example>", "Utilization update", "Fri, 20 Jun 2025 09:00:00 +0000",
         "Quick update.\n\nThe team increased the warehouse space utilization from 61% to 78%.\n")
    files.append(p)
    p = dest / "utilization_update_b.eml"
    _eml(p, "Site Manager <site.manager@northwind.example>", "Re: Utilization update", "Fri, 20 Jun 2025 11:30:00 +0000",
         "Checking my numbers.\n\nThe team increased the warehouse space utilization from 61% to 74%.\n")
    files.append(p)
    p = dest / "client_feedback.eml"
    _eml(p, "Priya Nair <priya.nair@heliosfreight.example>", "Feedback", "Mon, 23 Jun 2025 14:00:00 +0000",
         "Helios Freight's operations lead said, “The new dashboard gives my team a clear view of every order without "
         "chasing spreadsheets.” We are happy to discuss this further.\n")
    files.append(p)
    return files
