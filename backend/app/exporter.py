"""Approval-gated export. Nothing leaves the system unless a named human approved it item by item."""
import json
import zipfile
from pathlib import Path

from docx import Document

from .agents.privacy import redact
from .config import export_dir, ensure_dirs
from .db import now


def version_docx(v, path: Path):
    d = Document()
    d.add_heading(v["title"], 0)
    d.add_paragraph(f"Audience: {v['audience']}")
    for s in v["sections"]:
        d.add_heading(s["heading"], 1)
        for c in s["claims"]:
            cite = f" [{', '.join(c['refs'])}]" if c["refs"] else ""
            d.add_paragraph(c["text"] + cite, style="Quote" if c["type"] == "quote" else "List Bullet")
            if c.get("calc"):
                d.add_paragraph("Calculation: " + c["calc"])
    d.save(str(path))


def exportable(result, approvals):
    """Decide what may be exported. Returns (versions, assets, reasons_excluded)."""
    ok = {(a["item_type"], a["item_name"]) for a in approvals if a["status"] == "approved"}
    rejected_quotes = {a["item_name"] for a in approvals if a["item_type"] == "quote" and a["status"] != "approved"}
    versions, assets, excluded = [], [], []
    for v in result["versions"]:
        if ("version", v["key"]) not in ok:
            excluded.append(f"version {v['key']}: not approved")
        elif set(v["quote_refs"]) & rejected_quotes:
            excluded.append(f"version {v['key']}: contains a quote without client approval")
        else:
            versions.append(v)
    for a in result["assets"]:
        if ("asset", a["name"]) not in ok:
            excluded.append(f"asset {a['name']}: not approved")
        elif a["type"] == "quote_card" and set(a["refs"]) & rejected_quotes:
            excluded.append(f"asset {a['name']}: quote not approved")
        else:
            assets.append(a)
    return versions, assets, excluded


def build_export(project, run_id, result, approvals, reviewer):
    if not (reviewer or "").strip():
        raise PermissionError("A named human reviewer is required to export.")
    versions, assets, excluded = exportable(result, approvals)
    if not versions and not assets:
        raise PermissionError("Nothing is approved yet - approve at least one item before exporting.")
    ensure_dirs()
    red = result["privacy"]["redaction"]
    ev = {e["ref"]: e for e in result["evidence"]}
    cited = sorted({r for v in versions for s in v["sections"] for c in s["claims"] for r in c["refs"]} |
                   {r for a in assets for r in a["refs"]})
    sources = [{"ref": r, "document": redact(ev[r]["doc"], red)[0], "location": ev[r]["location"]} for r in cited]
    kpis = [{k: kp[k] for k in ("kpi", "baseline", "result", "unit", "calc", "refs", "status")} for kp in result["kpis"]
            if kp["usable"] and set(kp["refs"]) & set(cited)]
    zpath = export_dir() / f"project{project['id']}_run{run_id}_{now().replace(':', '').replace('-', '')}.zip"
    tmp = export_dir() / "_tmp"
    tmp.mkdir(exist_ok=True)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for v in versions:
            z.writestr(f"case_studies/{v['key']}.md", v["markdown"])
            dp = tmp / f"{v['key']}.docx"
            version_docx(v, dp)
            z.write(dp, f"case_studies/{v['key']}.docx")
            dp.unlink()
        for a in assets:
            z.write(a["path"], f"media/{a['name']}")
        z.writestr("evidence/sources_index.json", json.dumps(sources, indent=2))
        z.writestr("evidence/kpi_calculations.json", json.dumps(kpis, indent=2))
        z.writestr("approval_log.json", json.dumps(
            {"exported_by": reviewer, "exported_at": now(), "approvals": approvals, "excluded": excluded}, indent=2, default=str))
        z.writestr("README.txt", "Approved items only. Raw evidence text and the client approval pack are intentionally NOT included.\n")
    return zpath, excluded
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def add_table(doc, headers, rows):

    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Shading Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = str(header)

    for row in rows:
        cells = table.add_row().cells

        for i, value in enumerate(row):
            cells[i].text = str(value)

    return table


def export_case_study(data, output_path):

    doc = Document()

    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)

    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10)

    # TITLE PAGE
    title = doc.add_heading(
        "PROJECT DRISHTI", 0
    )

    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph(
        "AI-Powered Safety Camera & Gate Analytics"
    )

    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        f"Audience: {data['audience']}"
    )

    doc.add_paragraph(
        "January – September 2026"
    )

    doc.add_paragraph(
        f"Document Status: {data['approval_status']}"
    )

    doc.add_page_break()

    # EXECUTIVE SUMMARY
    doc.add_heading("1. Executive Summary", level=1)

    doc.add_paragraph(
        data["executive_summary"]
    )

    # BUSINESS CHALLENGE
    doc.add_heading("2. Business Challenge", level=1)

    doc.add_paragraph(
        data["business_challenge"]
    )

    # SOLUTION
    doc.add_heading("3. Solution Implemented", level=1)

    doc.add_paragraph(
        data["solution"]
    )

    # TIMELINE
    doc.add_heading("4. Project Timeline", level=1)

    timeline_rows = [
        [item["date"], item["event"], item["source"]]
        for item in data["timeline"]
    ]

    add_table(
        doc,
        ["Date", "Event", "Evidence Source"],
        timeline_rows
    )

    # RESULTS
    doc.add_heading("5. Measured Results", level=1)

    result_rows = [
        [
            item["kpi"],
            item["baseline"],
            item["final_value"],
            item["measurement_period"],
            item["source"]
        ]
        for item in data["results"]
    ]

    add_table(
        doc,
        [
            "KPI",
            "Baseline",
            "Final Value",
            "Measurement Period",
            "Source"
        ],
        result_rows
    )

    # CONTRIBUTING FACTORS
    doc.add_heading("6. Contributing Factors", level=1)

    for factor in data["contributing_factors"]:
        doc.add_paragraph(factor, style="List Bullet")

    # CONCLUSION
    doc.add_heading("7. Conclusion", level=1)

    doc.add_paragraph(
        data["conclusion"]
    )

    # EVIDENCE REFERENCES
    doc.add_heading("8. Evidence References", level=1)

    for source in data["sources"]:
        doc.add_paragraph(source, style="List Bullet")

    # CONFIDENTIALITY
    doc.add_paragraph()
    warning = doc.add_paragraph()

    run = warning.add_run(
        "CONFIDENTIAL: Draft for review. "
        "Not approved for external publication."
    )

    run.bold = True
    run.font.color.rgb = RGBColor(190, 40, 40)

    # FOOTER
    for sec in doc.sections:
        footer = sec.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("Project Drishti | Case Study")

    doc.save(output_path)

    return output_path
