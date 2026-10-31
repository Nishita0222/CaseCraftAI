import tempfile
from pathlib import Path

from app.demo_data import CLIENT, PROJECT, generate_demo_files
from app.extractors import kind_of
from app.pipeline import run_pipeline

_cache = {}


def demo_run(sequential=True):
    if "r" not in _cache:
        tmp = Path(tempfile.mkdtemp(prefix="cs_demo_"))
        files = [{"id": i, "filename": f.name, "path": str(f), "kind": kind_of(f)}
                 for i, f in enumerate(generate_demo_files(tmp))]
        proj = {"id": 1, "name": PROJECT, "client_name": CLIENT, "confidential_terms": "", "synthetic": 1}
        steps = []
        state = run_pipeline(proj, files, tmp / "out", lambda a, s, m: steps.append((a, s, m)), force_sequential=sequential)
        _cache["r"] = (state, steps, files, tmp)
    return _cache["r"]
