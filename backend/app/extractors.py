"""Document readers: PDF, DOCX (paragraphs + tables), XLSX, CSV, EML, TXT/MD.

Each reader returns (chunks, warnings). A chunk is a dict:
  location  - human-readable pointer used in citations ("p.2", "KPIs!row 3", "para 4" ...)
  text      - the text
  atomic    - True when the text must not be sentence-split (spreadsheet / table rows)
  row       - optional {header: value} for structured rows
  date      - optional ISO date (email sent date)
  metadata  - True for header-only chunks (never used as a claim)
"""
import csv
import html
import re
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path


def kind_of(path: Path) -> str:
    return {".pdf": "pdf", ".docx": "docx", ".xlsx": "xlsx", ".xlsm": "xlsx", ".eml": "eml",
            ".csv": "csv"}.get(path.suffix.lower(), "txt")


def _table_rows(header, body):
    for i, cells in enumerate(body, start=1):
        row = {h: c for h, c in zip(header, cells) if h}
        text = "; ".join(f"{h}: {c}" for h, c in row.items() if c not in (None, ""))
        if text:
            yield i, row, text


def read_pdf(path: Path):
    from pypdf import PdfReader
    chunks, warns = [], []
    for n, page in enumerate(PdfReader(str(path)).pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            warns.append(f"page {n} has no extractable text (scanned image? OCR is not enabled)")
            continue
        chunks.append({"location": f"p.{n}", "text": text})
    return chunks, warns


def read_docx(path: Path):
    from docx import Document
    doc = Document(str(path))
    chunks = []
    for i, p in enumerate(doc.paragraphs, start=1):
        if p.text.strip():
            chunks.append({"location": f"para {i}", "text": p.text.strip()})
    for t, table in enumerate(doc.tables, start=1):
        data = [[c.text.strip() for c in r.cells] for r in table.rows]
        if len(data) < 2:
            continue
        for r, row, text in _table_rows(data[0], data[1:]):
            chunks.append({"location": f"table {t} row {r}", "text": text, "atomic": True, "row": row,
                           "kind_hint": "table"})
    return chunks, []


def read_xlsx(path: Path):
    from openpyxl import load_workbook
    wb = load_workbook(str(path), data_only=True, read_only=True)
    chunks, warns = [], []
    for ws in wb.worksheets:
        data = [[("" if c is None else str(c).strip()) for c in r] for r in ws.iter_rows(values_only=True)]
        data = [r for r in data if any(r)]
        if len(data) < 2:
            continue
        for r, row, text in _table_rows(data[0], data[1:]):
            chunks.append({"location": f"{ws.title}!row {r + 1}", "text": text, "atomic": True, "row": row,
                           "kind_hint": "table"})
    return chunks, warns


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        data = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    chunks = []
    if len(data) >= 2:
        for r, row, text in _table_rows(data[0], data[1:]):
            chunks.append({"location": f"row {r + 1}", "text": text, "atomic": True, "row": row, "kind_hint": "table"})
    return chunks, []


def read_eml(path: Path):
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    subject = str(msg["subject"] or "(no subject)")
    iso = None
    try:
        iso = parsedate_to_datetime(str(msg["date"])).date().isoformat()
    except Exception:
        pass
    loc = f"email '{subject}'"
    people = [n for n in (parseaddr(str(msg["from"] or ""))[0], parseaddr(str(msg["to"] or ""))[0]) if n]
    header = f"From: {msg['from']} | To: {msg['to']} | Subject: {subject} | Date: {msg['date']}"
    chunks = [{"location": loc + " (headers)", "text": header, "atomic": True, "metadata": True,
               "date": iso, "people": people}]
    body = msg.get_body(preferencelist=("plain", "html"))
    content = body.get_content() if body else ""
    if body is not None and body.get_content_type() == "text/html":
        content = html.unescape(re.sub(r"<[^>]+>", " ", content))
    for para in re.split(r"\n\s*\n", content):
        lines = [l for l in para.splitlines() if not l.strip().startswith(">")]
        text = " ".join(l.strip() for l in lines).strip()
        if text:
            chunks.append({"location": loc, "text": text, "date": iso})
    return chunks, []


def read_text(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return [{"location": f"para {i}", "text": p.strip()}
            for i, p in enumerate(re.split(r"\n\s*\n", text), start=1) if p.strip()], []


def extract_document(path: Path):
    k = kind_of(path)
    reader = {"pdf": read_pdf, "docx": read_docx, "xlsx": read_xlsx, "eml": read_eml, "csv": read_csv}.get(k, read_text)
    return reader(path)
