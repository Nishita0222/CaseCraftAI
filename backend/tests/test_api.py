"""API tests - run automatically when fastapi + httpx are installed (pip install -r requirements.txt)."""
import time
import unittest

from tests import conftest  # noqa: F401

try:
    from fastapi.testclient import TestClient
    from app.main import app
    HAVE = True
except Exception:  # pragma: no cover
    HAVE = False


@unittest.skipUnless(HAVE, "fastapi/httpx not installed")
class ApiTests(unittest.TestCase):
    def test_full_flow(self):
        with TestClient(app) as c:
            self.assertEqual(c.get("/api/health").json()["status"], "ok")
            p = c.post("/api/demo").json()
            self.assertEqual(len(p["documents"]), 7)
            c.post(f"/api/projects/{p['id']}/run")
            for _ in range(60):
                run = c.get(f"/api/projects/{p['id']}/runs/latest").json()
                if run["status"] in ("completed", "failed"):
                    break
                time.sleep(0.5)
            self.assertEqual(run["status"], "completed", run.get("error"))
            self.assertEqual(len(run["result"]["versions"]), 3)
            self.assertNotIn("path", run["result"]["assets"][0])
            # export is refused before any approval
            self.assertEqual(c.post(f"/api/projects/{p['id']}/export", json={"reviewer": "R"}).status_code, 403)
            items = c.get(f"/api/projects/{p['id']}/approvals").json()
            r = c.post(f"/api/approvals/{items[0]['id']}/decision", json={"status": "approved", "reviewer": "", "comment": ""})
            self.assertEqual(r.status_code, 422)  # reviewer name required
            for it in items:
                c.post(f"/api/approvals/{it['id']}/decision", json={"status": "approved", "reviewer": "Dana", "comment": ""})
            ex = c.post(f"/api/projects/{p['id']}/export", json={"reviewer": "Dana"})
            self.assertEqual(ex.status_code, 200)
            self.assertEqual(c.get(ex.json()["download"]).status_code, 200)

    def test_rejects_bad_upload(self):
        with TestClient(app) as c:
            p = c.post("/api/projects", json={"name": "x"}).json()
            r = c.post(f"/api/projects/{p['id']}/documents", files={"files": ("evil.exe", b"MZ", "application/octet-stream")})
            self.assertEqual(r.status_code, 415)
