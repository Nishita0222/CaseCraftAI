"""SQLite persistence (stdlib sqlite3). One short-lived connection per call/thread."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import db_path, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, client_name TEXT DEFAULT '',
  confidential_terms TEXT DEFAULT '', synthetic INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  filename TEXT, stored_path TEXT, kind TEXT, size INTEGER, sha256 TEXT, uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  status TEXT, engine TEXT, started_at TEXT, finished_at TEXT, error TEXT, result_json TEXT);
CREATE TABLE IF NOT EXISTS steps(
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  agent TEXT, label TEXT, status TEXT, message TEXT, started_at TEXT, finished_at TEXT, position INTEGER);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, run_id INTEGER NOT NULL,
  item_type TEXT, item_name TEXT, description TEXT, status TEXT DEFAULT 'pending',
  reviewer TEXT, comment TEXT, decided_at TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, actor TEXT, action TEXT, detail TEXT, created_at TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def get_db():
    ensure_dirs()
    conn = sqlite3.connect(db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as c:
        c.executescript(SCHEMA)


def rows(cur) -> list:
    return [dict(r) for r in cur.fetchall()]


# ---- projects / documents ---------------------------------------------------
def create_project(name, client_name="", confidential_terms="", synthetic=False) -> dict:
    with get_db() as c:
        cur = c.execute(
            "INSERT INTO projects(name,client_name,confidential_terms,synthetic,created_at) VALUES(?,?,?,?,?)",
            (name, client_name, confidential_terms, int(synthetic), now()))
        pid = cur.lastrowid
    audit(pid, "system", "project_created", name)
    return get_project(pid)


def list_projects() -> list:
    with get_db() as c:
        return rows(c.execute("SELECT * FROM projects ORDER BY id DESC"))


def get_project(pid: int):
    with get_db() as c:
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None


def delete_project(pid: int) -> None:
    with get_db() as c:
        c.execute("DELETE FROM approvals WHERE project_id=?", (pid,))
        c.execute("DELETE FROM projects WHERE id=?", (pid,))


def add_document(pid, filename, stored_path, kind, size, sha256) -> dict:
    with get_db() as c:
        cur = c.execute(
            "INSERT INTO documents(project_id,filename,stored_path,kind,size,sha256,uploaded_at) VALUES(?,?,?,?,?,?,?)",
            (pid, filename, str(stored_path), kind, size, sha256, now()))
        did = cur.lastrowid
    audit(pid, "user", "document_uploaded", filename)
    return get_document(did)


def get_document(did: int):
    with get_db() as c:
        r = c.execute("SELECT * FROM documents WHERE id=?", (did,)).fetchone()
        return dict(r) if r else None


def list_documents(pid: int) -> list:
    with get_db() as c:
        return rows(c.execute("SELECT * FROM documents WHERE project_id=? ORDER BY id", (pid,)))


def delete_document(did: int) -> None:
    with get_db() as c:
        c.execute("DELETE FROM documents WHERE id=?", (did,))


# ---- runs ---------------------------------------------------------------------
def create_run(pid: int, agents: list) -> dict:
    with get_db() as c:
        cur = c.execute("INSERT INTO runs(project_id,status,started_at) VALUES(?,?,?)", (pid, "queued", now()))
        rid = cur.lastrowid
        for i, (name, label) in enumerate(agents):
            c.execute("INSERT INTO steps(run_id,agent,label,status,position) VALUES(?,?,?,?,?)",
                      (rid, name, label, "pending", i))
    audit(pid, "user", "run_started", f"run {rid}")
    return get_run(rid)


def update_step(run_id: int, agent: str, status: str, message=None) -> None:
    with get_db() as c:
        if status == "running":
            c.execute("UPDATE steps SET status=?,started_at=? WHERE run_id=? AND agent=?", (status, now(), run_id, agent))
        else:
            c.execute("UPDATE steps SET status=?,message=?,finished_at=? WHERE run_id=? AND agent=?",
                      (status, message, now(), run_id, agent))


def set_run(run_id: int, **fields) -> None:
    if "result" in fields:
        fields["result_json"] = json.dumps(fields.pop("result"), default=str)
    cols = ",".join(f"{k}=?" for k in fields)
    with get_db() as c:
        c.execute(f"UPDATE runs SET {cols} WHERE id=?", (*fields.values(), run_id))


def get_run(run_id: int, with_result=False):
    with get_db() as c:
        r = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not r:
            return None
        run = dict(r)
        run["steps"] = rows(c.execute("SELECT * FROM steps WHERE run_id=? ORDER BY position", (run_id,)))
    raw = run.pop("result_json", None)
    if with_result:
        run["result"] = json.loads(raw) if raw else None
    return run


def latest_run(pid: int, with_result=False):
    with get_db() as c:
        r = c.execute("SELECT id FROM runs WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    return get_run(r["id"], with_result) if r else None


# ---- approvals / audit ----------------------------------------------------------
def create_approvals(pid: int, run_id: int, items: list) -> None:
    with get_db() as c:
        for it in items:
            c.execute("INSERT INTO approvals(project_id,run_id,item_type,item_name,description,created_at) VALUES(?,?,?,?,?,?)",
                      (pid, run_id, it["item_type"], it["item_name"], it.get("description", ""), now()))


def list_approvals(pid: int, run_id=None) -> list:
    with get_db() as c:
        if run_id:
            return rows(c.execute("SELECT * FROM approvals WHERE project_id=? AND run_id=? ORDER BY id", (pid, run_id)))
        return rows(c.execute("SELECT * FROM approvals WHERE project_id=? ORDER BY id", (pid,)))


def get_approval(aid: int):
    with get_db() as c:
        r = c.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone()
        return dict(r) if r else None


def decide_approval(aid: int, status: str, reviewer: str, comment: str = "") -> dict:
    if status not in ("approved", "rejected", "pending"):
        raise ValueError("status must be approved, rejected or pending")
    if status != "pending" and not (reviewer or "").strip():
        raise ValueError("A named human reviewer is required")
    with get_db() as c:
        c.execute("UPDATE approvals SET status=?,reviewer=?,comment=?,decided_at=? WHERE id=?",
                  (status, (reviewer or "").strip(), comment, now(), aid))
    a = get_approval(aid)
    audit(a["project_id"], reviewer, f"approval_{status}", f"{a['item_type']}:{a['item_name']} {comment}".strip())
    return a


def audit(pid, actor, action, detail="") -> None:
    with get_db() as c:
        c.execute("INSERT INTO audit_log(project_id,actor,action,detail,created_at) VALUES(?,?,?,?,?)",
                  (pid, actor, action, detail, now()))


def list_audit(pid: int) -> list:
    with get_db() as c:
        return rows(c.execute("SELECT * FROM audit_log WHERE project_id=? ORDER BY id DESC LIMIT 300", (pid,)))
