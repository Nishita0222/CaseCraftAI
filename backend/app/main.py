"""FastAPI application. Bind to 127.0.0.1 only: project files are confidential and stay local."""
import hashlib
import re
import shutil
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import db
from .config import ALLOWED_EXT, MAX_UPLOAD_MB, ensure_dirs, export_dir, output_dir, upload_dir
from .demo_data import CLIENT, PROJECT, generate_demo_files
from .exporter import build_export
from .extractors import kind_of
from .pipeline import agent_list, run_pipeline

@asynccontextmanager
async def lifespan(_app):
    ensure_dirs()
    db.init_db()
    yield


app = FastAPI(
    title="CaseCraft AI",
    description="AI-Powered Evidence-Backed Case Study Generation Platform",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


class ProjectIn(BaseModel):
    name: str
    client_name: str = ""
    confidential_terms: str = ""


class DecisionIn(BaseModel):
    status: str
    reviewer: str
    comment: str = ""


class ExportIn(BaseModel):
    reviewer: str


def _project(pid):
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "Project not found")
    return p


def _save_file(pid: int, filename: str, data: bytes):
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(filename).name)[:120] or "file"
    if Path(name).suffix.lower() not in ALLOWED_EXT:
        raise HTTPException(415, f"Unsupported file type: {name}. Allowed: {', '.join(sorted(ALLOWED_EXT))}")
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"{name} exceeds {MAX_UPLOAD_MB} MB")
    sha = hashlib.sha256(data).hexdigest()
    if any(d["sha256"] == sha for d in db.list_documents(pid)):
        return None
    folder = upload_dir() / f"project_{pid}"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex[:8]}_{name}"
    path.write_bytes(data)
    return db.add_document(pid, name, path, kind_of(path), len(data), sha)


@app.get("/api/health")
def health():
    try:
        import langgraph  # noqa: F401
        engine = "langgraph"
    except ImportError:
        engine = "sequential-fallback"
    return {"status": "ok", "engine": engine}


@app.get("/api/agents")
def agents():
    return [{"name": n, "label": l} for n, l in agent_list()]


@app.get("/api/projects")
def projects():
    return db.list_projects()


@app.post("/api/projects")
def new_project(body: ProjectIn):
    if not body.name.strip():
        raise HTTPException(422, "Project name is required")
    return db.create_project(body.name.strip(), body.client_name.strip(), body.confidential_terms.strip())


@app.get("/api/projects/{pid}")
def project(pid: int):
    return {**_project(pid), "documents": db.list_documents(pid)}


@app.delete("/api/projects/{pid}")
def remove_project(pid: int):
    _project(pid)
    db.delete_project(pid)
    shutil.rmtree(upload_dir() / f"project_{pid}", ignore_errors=True)
    shutil.rmtree(output_dir() / f"project_{pid}", ignore_errors=True)
    return {"deleted": pid}


@app.post("/api/projects/{pid}/documents")
async def upload(pid: int, files: list[UploadFile] = File(...)):
    _project(pid)
    saved, skipped = [], []
    for f in files:
        doc = _save_file(pid, f.filename or "file", await f.read())
        (saved if doc else skipped).append(doc or f.filename)
    return {"saved": saved, "skipped_duplicates": skipped}


@app.delete("/api/documents/{did}")
def remove_document(did: int):
    d = db.get_document(did)
    if not d:
        raise HTTPException(404, "Document not found")
    Path(d["stored_path"]).unlink(missing_ok=True)
    db.delete_document(did)
    return {"deleted": did}


@app.post("/api/demo")
def demo():
    """Create a project from SYNTHETIC files only."""
    p = db.create_project(PROJECT, CLIENT, "", synthetic=True)
    with tempfile.TemporaryDirectory() as tmp:
        for f in generate_demo_files(Path(tmp)):
            _save_file(p["id"], f.name, f.read_bytes())
    return project(p["id"])


def execute_run(run_id: int, pid: int):
    p = db.get_project(pid)
    files = [{"id": d["id"], "filename": d["filename"], "path": d["stored_path"], "kind": d["kind"]}
             for d in db.list_documents(pid)]
    db.set_run(run_id, status="running")

    def on_step(agent, status, message):
        db.update_step(run_id, agent, status, message)

    try:
        out = output_dir() / f"project_{pid}" / f"run_{run_id}"
        final = run_pipeline(p, files, out, on_step)
        result = {k: final.get(k) for k in ("evidence", "documents", "warnings", "timeline", "undated", "scope_changes",
                                           "span", "kpis", "privacy", "versions", "quotes", "assets", "approval_pack",
                                           "approval_items", "validation")}
        db.create_approvals(pid, run_id, final["approval_items"])
        db.set_run(run_id, status="completed", engine=final["engine"], finished_at=db.now(), result=result)
        db.audit(pid, "system", "run_completed", f"run {run_id}")
    except Exception as e:
        db.set_run(run_id, status="failed", finished_at=db.now(), error=f"{type(e).__name__}: {e}")
        db.audit(pid, "system", "run_failed", str(e))


@app.post("/api/projects/{pid}/run")
def start_run(pid: int, bg: BackgroundTasks):
    _project(pid)
    if not db.list_documents(pid):
        raise HTTPException(422, "Upload at least one document first")
    run = db.create_run(pid, agent_list())
    bg.add_task(execute_run, run["id"], pid)
    return run


@app.get("/api/projects/{pid}/runs/latest")
def latest(pid: int):
    _project(pid)
    run = db.latest_run(pid, with_result=True)
    if not run:
        return None
    if run.get("result"):  # asset file paths stay server-side
        for a in run["result"]["assets"]:
            a.pop("path", None)
        run["result"].pop("approval_pack", None)
    return run


@app.get("/api/projects/{pid}/approvals")
def approvals(pid: int):
    _project(pid)
    run = db.latest_run(pid)
    return db.list_approvals(pid, run["id"]) if run else []


@app.post("/api/approvals/{aid}/decision")
def decide(aid: int, body: DecisionIn):
    if not db.get_approval(aid):
        raise HTTPException(404, "Approval item not found")
    try:
        return db.decide_approval(aid, body.status, body.reviewer, body.comment)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/projects/{pid}/assets/{name}")
def asset(pid: int, name: str):
    run = db.latest_run(pid, with_result=True)
    assets = ((run or {}).get("result") or {}).get("assets", [])
    a = next((x for x in assets if x["name"] == name), None)
    if not a or not Path(a["path"]).exists():
        raise HTTPException(404, "Asset not found")
    return FileResponse(a["path"])


@app.get("/api/projects/{pid}/approval-pack")
def approval_pack(pid: int):
    run = db.latest_run(pid, with_result=True)
    if not run or not run.get("result"):
        raise HTTPException(404, "No completed run")
    return FileResponse(run["result"]["approval_pack"]["docx"], filename="client_approval_pack.docx")


@app.post("/api/projects/{pid}/export")
def export(pid: int, body: ExportIn):
    p = _project(pid)
    run = db.latest_run(pid, with_result=True)
    if not run or run["status"] != "completed":
        raise HTTPException(409, "No completed run to export")
    try:
        zpath, excluded = build_export(p, run["id"], run["result"], db.list_approvals(pid, run["id"]), body.reviewer)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    db.audit(pid, body.reviewer, "exported", f"{zpath.name}; excluded: {len(excluded)}")
    return {"file": zpath.name, "excluded": excluded, "download": f"/api/exports/{zpath.name}"}


@app.get("/api/exports/{name}")
def download(name: str):
    path = export_dir() / Path(name).name
    if not path.exists():
        raise HTTPException(404, "Export not found")
    return FileResponse(path, filename=path.name)


@app.get("/api/projects/{pid}/audit")
def audit_log(pid: int):
    _project(pid)
    return db.list_audit(pid)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from pathlib import Path

from exporter import export_case_study


app = FastAPI(
    title="Project Drishti Case Study Export API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


OUTPUT_DIR = Path("generated_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


# DATA MODELS

class TimelineItem(BaseModel):
    date: str
    event: str
    source: str


class KPIResult(BaseModel):
    kpi: str
    baseline: str
    final_value: str
    measurement_period: str
    source: str


class CaseStudy(BaseModel):

    audience: str

    executive_summary: str
    business_challenge: str
    solution: str

    timeline: List[TimelineItem]
    results: List[KPIResult]

    contributing_factors: List[str]
    conclusion: str
    sources: List[str]

    approval_status: str = "Pending Human Approval"


# SAMPLE DATA
# Replace this with verified output from your AI agents.

CASE_STUDY_DATA = {

    "executive_summary":
    "Project Drishti explores AI-powered safety cameras "
    "and gate analytics in a cement manufacturing environment.",

    "business_challenge":
    "The project focuses on vehicle movement monitoring, "
    "gate visibility and operational safety.",

    "solution":
    "An AI-enabled camera and gate analytics solution "
    "was proposed for monitoring industrial operations.",

    "timeline": [
        {
            "date": "January 2026",
            "event": "Project initiation",
            "source": "Project proposal"
        },
        {
            "date": "February 2026",
            "event": "Implementation activities started",
            "source": "Project tracker"
        }
    ],

    "results": [
        {
            "kpi": "Gate Processing Time",
            "baseline": "Not verified",
            "final_value": "Not verified",
            "measurement_period": "Not available",
            "source": "No verified KPI source"
        }
    ],

    "contributing_factors": [
        "AI-based monitoring approach",
        "Gate analytics implementation"
    ],

    "conclusion":
    "Final project impact must be established using "
    "verified project records.",

    "sources": [
        "Project proposal",
        "Project tracker"
    ]
}


@app.get("/")
def home():

    return {
        "message": "Project Drishti API is running"
    }


@app.get("/api/case-study")
def get_case_study():

    return CASE_STUDY_DATA


@app.post("/api/export/{audience}")
def generate_word(audience: str):

    allowed = [
        "gatekeeper",
        "user",
        "buyer"
    ]

    if audience.lower() not in allowed:

        raise HTTPException(
            status_code=400,
            detail="Invalid audience selection"
        )

    data = CASE_STUDY_DATA.copy()

    data["audience"] = audience.capitalize()

    filename = f"Drishti_{audience}.docx"

    output_path = OUTPUT_DIR / filename

    try:

        export_case_study(
            data,
            str(output_path)
        )

        return {
            "message": "Word document generated successfully",
            "filename": filename,
            "download_url": f"/api/download/{filename}"
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/api/download/{filename}")
def download_word(filename: str):

    allowed_files = [
        "Drishti_gatekeeper.docx",
        "Drishti_user.docx",
        "Drishti_buyer.docx"
    ]

    if filename not in allowed_files:

        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    file_path = OUTPUT_DIR / filename

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Generate the document first"
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
    )
