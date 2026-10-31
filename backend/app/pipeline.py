"""LangGraph orchestration. Falls back to a plain sequential runner if langgraph is not installed."""
from .agents import approval, document_reader, kpi, media, privacy, recheck, timeline, writer
from .agents.state import CaseState

# (node name, label, description, function) - node names deliberately differ from state keys
AGENTS = [
    ("document_reader", "Document Reader", "Extract text from PDF / DOCX / XLSX / email into citable evidence", document_reader.run),
    ("timeline_scope", "Timeline & Scope", "Build the project timeline and detect scope changes", timeline.run),
    ("kpi_verifier", "KPI Verifier", "Recalculate KPIs and resolve conflicting evidence", kpi.run),
    ("privacy_guard", "Privacy Guard", "Detect confidential information; apply NDA / privacy rules", privacy.run),
    ("case_writer", "Case Writer", "Draft Gatekeeper, User and Buyer versions from verified claims", writer.run),
    ("privacy_recheck", "Privacy Re-check", "Re-scan generated text for leaks", recheck.run),
    ("media_studio", "Media Studio", "Create charts, timeline and infographic assets", media.run),
    ("approval_packager", "Approval Packager", "Prepare client approval documents", approval.run),
]


def agent_list():
    return [(a[0], a[1]) for a in AGENTS]


def _wrap(name, fn, on_step):
    def node(state):
        on_step(name, "running", None)
        try:
            updates, summary = fn(state)
        except Exception as e:
            on_step(name, "failed", f"{type(e).__name__}: {e}")
            raise
        on_step(name, "done", summary)
        return updates
    return node


def build_graph(on_step):
    from langgraph.graph import END, StateGraph
    g = StateGraph(CaseState)
    for name, _label, _desc, fn in AGENTS:
        g.add_node(name, _wrap(name, fn, on_step))
    g.set_entry_point(AGENTS[0][0])
    for a, b in zip(AGENTS, AGENTS[1:]):
        g.add_edge(a[0], b[0])
    g.add_edge(AGENTS[-1][0], END)
    return g.compile()


def run_pipeline(project, files, output_dir, on_step=None, force_sequential=False):
    on_step = on_step or (lambda *a: None)
    state = {"project": project, "files": files, "output_dir": str(output_dir)}
    try:
        if force_sequential:
            raise ImportError
        app = build_graph(on_step)
        engine = "langgraph"
    except ImportError:
        app, engine = None, "sequential-fallback"
    if app is not None:
        final = app.invoke(state)
    else:
        final = dict(state)
        for name, _l, _d, fn in AGENTS:
            final.update(_wrap(name, fn, on_step)(final))
    final["engine"] = engine
    return final
