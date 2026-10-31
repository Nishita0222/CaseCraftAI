"""Agent 8 - Approval Packager: client approval pack (.docx), cover note, approval checklist items."""
from pathlib import Path

from docx import Document
from docx.shared import Pt


def _table(doc, header, rows):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = h
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    return t


def build_pack(state, path: Path):
    p, ev = state["project"], {e["ref"]: e for e in state["evidence"]}
    doc = Document()
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading(f"Client Approval Pack - {p['name']}", 0)
    if p.get("synthetic"):
        doc.add_paragraph("SYNTHETIC DEMO DATA - not a real client engagement.")
    doc.add_paragraph("CONFIDENTIAL - for the named client approver only. Nothing in this pack may be published, "
                      "exported or shared until every item below is approved in writing.")
    doc.add_heading("1. What you are asked to approve", 1)
    _table(doc, ["Item", "Type", "Decision (tick one)"],
           [(i["item_name"], i["item_type"], "[ ] Approve   [ ] Approve with changes   [ ] Reject") for i in state["approval_items"]])
    doc.add_heading("2. Claims and the evidence behind them", 1)
    for v in state["versions"]:
        doc.add_heading(f"{v['title']} ({v['audience']}) - {v['status']}", 2)
        rows = []
        for s in v["sections"]:
            for c in s["claims"]:
                if c["type"] == "boilerplate":
                    continue
                src = "; ".join(f"{r}: {ev[r]['doc']} @ {ev[r]['location']}" for r in c["refs"])
                rows.append((c["text"], src))
        if rows:
            _table(doc, ["Claim", "Source(s)"], rows)
    doc.add_heading("3. KPI verification", 1)
    _table(doc, ["KPI", "Baseline", "Result", "Calculation", "Status", "Notes"],
           [(k["kpi"], k["baseline"], k["result"], k["calc"], k["status"],
             " ".join([k["rationale"]] + k["warnings"])) for k in state["kpis"]])
    doc.add_heading("4. Privacy and NDA treatment", 1)
    for r in state["privacy"]["rules"]:
        doc.add_paragraph(r, style="List Bullet")
    doc.add_paragraph("Findings by type: " + (", ".join(f"{k}={v}" for k, v in state["privacy"]["counts"].items()) or "none"))
    doc.add_heading("5. Quotes - consent", 1)
    if state.get("quotes"):
        for q in state["quotes"]:
            doc.add_paragraph(f"“{q['quote']}” - {q['attribution']} (source {q['ref']})")
        doc.add_paragraph("I consent to the use of the quote(s) above:  [ ] Yes   [ ] No")
    else:
        doc.add_paragraph("No verified client quotes were found.")
    doc.add_heading("6. Sign-off", 1)
    doc.add_paragraph("Name: ____________________   Role: ____________________")
    doc.add_paragraph("Signature: ____________________   Date: ____________________")
    doc.save(str(path))


def run(state):
    out = Path(state["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    items = []
    for v in state["versions"]:
        if v["status"] == "ready_for_review":
            items.append({"item_type": "version", "item_name": v["key"], "description": v["title"]})
    for a in state["assets"]:
        if a["status"] == "ready_for_review":
            items.append({"item_type": "asset", "item_name": a["name"], "description": a["caption"]})
    for q in state.get("quotes", []):
        items.append({"item_type": "quote", "item_name": q["ref"], "description": "Client quote - written consent needed"})
    state = {**state, "approval_items": items}
    pack = out / "client_approval_pack.docx"
    build_pack(state, pack)
    note = out / "client_cover_note.txt"
    note.write_text(
        f"Subject: Approval request - case study for {state['project']['name']}\n\n"
        "Hello,\n\nPlease find attached our draft case study material and an approval pack. Each claim cites the project "
        "document it comes from and shows its calculation. Client identity and confidential terms have been withheld.\n"
        "Nothing will be published or shared until you approve each item in writing.\n\nKind regards\n", encoding="utf-8")
    validation = {
        "versions_grounded": all(v["grounding"]["ok"] for v in state["versions"]),
        "privacy_recheck_passed": state["privacy"]["recheck"]["passed"] and all(a["privacy_recheck"]["passed"] for a in state["assets"]),
        "assets_created": len(state["assets"]),
        "assets_requirement_met": len(state["assets"]) >= 3,
        "human_approval_required": True}
    return ({"approval_items": items, "approval_pack": {"docx": str(pack), "cover_note": str(note)}, "validation": validation},
            f"Approval pack + cover note created; {len(items)} item(s) await human approval")
