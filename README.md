# CaseCraft AI — Evidence-Backed Case Study Generation Platform
**CaseCraft AI** transforms unstructured project documents into
verified, evidence-backed case studies for different audiences.

It uses eight specialized agents for document extraction,
timeline analysis, KPI verification, privacy enforcement,
case study generation, media creation and human approval.

Turns messy project documents (PDF, DOCX, XLSX, emails) into **evidence-backed case studies** for three audiences,
with KPI verification, NDA/privacy enforcement, media assets and a **human approval gate** before anything is exported.

> **Core rule: nothing is invented.** The agents are deterministic (regex + arithmetic + templates). Every sentence,
> number, date and quote in an output is traced to an evidence ID (`E012`) and re-checked by a grounding validator.
> If the evidence is missing, conflicting or confidential, the claim is **left out** and the reason is shown.

---
## Quick start

**Requirements:** Python 3.10+, Node 18+.

```bash
# 1. Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Frontend (terminal 2)
cd frontend
npm install
npm run dev                                              # http://localhost:5173
```
Open http://localhost:5173 → **Load synthetic demo** → **Run all agents** → review the tabs → approve items → export.

Or use `./setup.sh` once, then `./run_backend.sh` and `./run_frontend.sh`.

**Tests:** `cd backend && python -m pytest -v` (or `python -m unittest discover -s tests -t .`).

---
## The 8 LangGraph agents (`backend/app/pipeline.py`)
| # | Node | What it does |
|---|------|--------------|
| 1 | `document_reader` | Reads PDF (pypdf), DOCX paragraphs + tables (python-docx), XLSX (openpyxl), CSV, EML, TXT → numbered **evidence items** with document + location. |
| 2 | `timeline_scope` | Parses dates *stated in the text* (ISO, `12 March 2025`, `March 12, 2025`), builds the timeline, computes the project span, detects **scope changes** (change requests, additions, descoping). |
| 3 | `kpi_verifier` | Finds KPI claims (spreadsheet/table rows and "reduced X from A to B" sentences), **recalculates** change with `Decimal`, flags wrong stated percentages, and **resolves conflicts** by source authority. Unresolved conflicts are excluded. |
| 4 | `privacy_guard` | Detects emails, phones, person names, client name, custom confidential terms, NDA clauses, contract/price amounts. Builds redaction rules; blocks KPIs referenced by an NDA clause. |
| 5 | `case_writer` | Builds **Gatekeeper / User / Buyer** versions from verified claims only (templates, not free text). Quotes are verbatim and flagged for client consent. |
| 6 | `privacy_recheck` | Re-scans every generated text; any leak blocks the output. |
| 7 | `media_studio` | Matplotlib assets from verified data only: KPI chart, headline infographic, timeline, quote card (≥3 required, warns otherwise). |
| 8 | `approval_packager` | Client approval pack (.docx: claims + sources, KPI calculations, privacy treatment, consent + sign-off), cover note, and approval checklist items. |

If `langgraph` is not installed the same nodes run in a plain sequential loop (`engine: sequential-fallback` is shown in the UI).

### KPI conflict-resolution rule
`authority = source base (Excel/table 3, PDF 2, DOCX 2, email 1) +1 for "final/verified/measured", −1 for "preliminary/estimate"`.
Highest authority wins if all top-ranked claims agree (`conflict_resolved`); equal-authority disagreement is `unresolved` and never published;
estimate-only KPIs are excluded. Every decision shows its calculation, e.g. `(48 - 12) / 48 x 100 = 75.0% reduction`.

### Anti-hallucination guarantees
1. No generative model writes facts. Text is assembled from evidence + arithmetic.
2. `validators.py` rejects any claim without a citation, with a number not present in its cited evidence/calculation, a date not in the evidence, or a non-verbatim quote (tested).
3. Confidential content is excluded *before* writing and re-scanned *after* writing.
4. Source limitations are visible: single-source KPIs, wrong stated %, unresolved conflicts, skipped quotes.

*(Optional extension: an LLM could be added for prose polishing — its output would still have to pass `validate_version`.)*

---
## Dashboard tabs
Workflow (live agent tracking) · Documents (drag-and-drop upload) · Evidence (searchable register, click any citation chip) ·
Timeline & Scope · KPI Report (with calculations) · Privacy (findings, rules, re-check) · Case Studies (3 previews with citations) ·
Media · Approvals (per-item human decisions, approval pack download, gated export, audit trail).

## Confidentiality & approval model
* Everything is stored locally: SQLite (`backend/data/casestudy.db`), uploads, outputs, exports. The API binds to `127.0.0.1`; CORS allows only localhost.
* No network calls to AI services. Real project files are never sent anywhere.
* Demo data is **synthetic** (fictional "Helios Freight"), generated by `app/demo_data.py` and labelled on every asset.
* **Export requires a named reviewer and per-item approval.** Only approved items are exported; versions containing an unapproved quote are excluded.
  Exports contain no raw evidence text and no approval pack — only redacted outputs, a sources index (document + location), KPI calculations and the approval log.
* Re-running the agents creates a new set of approval items (old approvals do not carry over).

## API (FastAPI, docs at http://127.0.0.1:8000/docs)
`POST /api/projects` · `POST /api/demo` · `POST /api/projects/{id}/documents` · `POST /api/projects/{id}/run` ·
`GET /api/projects/{id}/runs/latest` · `GET /api/projects/{id}/approvals` · `POST /api/approvals/{id}/decision` ·
`GET /api/projects/{id}/approval-pack` · `POST /api/projects/{id}/export` · `GET /api/projects/{id}/audit`

## Folder structure
```
backend/app/   main.py (API) · pipeline.py (LangGraph) · db.py (SQLite) · extractors.py · validators.py
               exporter.py · demo_data.py · agents/ (8 agents + common/state)
backend/tests/ extractor, pipeline (KPI/privacy/grounding), workflow (approval/export), API tests
frontend/src/  App.jsx · api.js · components/ (one file per tab)
```

## Known limits (be honest with judges)
* Extraction is rule-based: KPI sentences must look like *"reduced/increased/improved … from A to B"* or be in a KPI/Baseline/Result table. Other phrasing is missed (and therefore not claimed).
* Scanned PDFs need OCR (not included; a warning is shown). Spreadsheet formulas need cached values (save in Excel first).
* Person-name detection is heuristic (names after "said", titles, email display names); add anything else under *Extra confidential terms*.
* Metric names are grouped after light normalization; very different wording for the same KPI will appear as separate KPIs.
