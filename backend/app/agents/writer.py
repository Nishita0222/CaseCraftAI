"""Agent 5 - Case Writer: three audience versions built ONLY from verified KPIs + cited evidence.

No free-text generation: each claim is a template filled with values taken from the evidence, so nothing can be
invented. (An LLM could be plugged in for style, but validators.py would still have to pass.)
"""
import re
from decimal import Decimal

from ..text_utils import fmt_val
from ..validators import validate_version
from .common import QUOTE_VERB
from .privacy import redact

QUOTE_RE = re.compile(r"[“\"]([^”\"]{25,300}?)[”\"]")
AFTER_ATTR = re.compile(rf"^[\s,]*{QUOTE_VERB}\b(?P<who>[^.]*)", re.I)
BEFORE_ATTR = re.compile(rf"\s*{QUOTE_VERB}\W*$", re.I)


def find_quotes(evidence, restricted, red):
    quotes, notes = [], []
    for e in evidence:
        if e["metadata"] or e.get("row") or e["ref"] in restricted:
            continue
        for m in QUOTE_RE.finditer(e["text"]):
            q = m.group(1).strip()
            before, after = e["text"][:m.start()], e["text"][m.end():]
            if len(q.split()) < 6 or not (BEFORE_ATTR.search(before) or AFTER_ATTR.match(after)):
                continue
            if redact(q, red)[0] != q:
                notes.append(f"Quote in {e['ref']} skipped: it contains confidential details (altering a quote is not allowed).")
                continue
            who = BEFORE_ATTR.sub("", before).strip(" ,:") if BEFORE_ATTR.search(before) else (AFTER_ATTR.match(after).group("who").strip(" ,"))
            who = redact(who, red)[0]
            if not who or "[name withheld]" in who or len(who) > 60:
                who = "a client stakeholder"
            quotes.append({"ref": e["ref"], "quote": q, "attribution": who, "doc": e["doc"], "location": e["location"]})
    return quotes, notes


def _kpi_claim(k, red):
    name = redact(k["kpi"], red)[0]
    a, b, u = Decimal(k["baseline"]), Decimal(k["result"]), k["unit"]
    text = f"{name} {k['direction']} from {fmt_val(a, u)} to {fmt_val(b, u)}"
    if k["pct_change"]:
        text += f" ({k['pct_change']}% {k['noun']})"
    return {"text": text + ".", "refs": k["refs"], "type": "kpi", "calc": k["calc"], "kpi_id": k["id"]}


def _line(text, refs, typ, **kw):
    return {"text": text, "refs": refs, "type": typ, **kw}


def _quote_claim(q):
    return {"text": f"“{q['quote']}” — {q['attribution']}", "refs": [q["ref"]], "type": "quote",
            "quote": q["quote"], "needs_client_approval": True}


def _md(v):
    out = [f"# {v['title']}", f"*Audience: {v['audience']}*", ""]
    for s in v["sections"]:
        out.append(f"## {s['heading']}")
        for c in s["claims"]:
            cite = f" [{', '.join(c['refs'])}]" if c["refs"] else ""
            out.append(f"> {c['text']}{cite}" if c["type"] == "quote" else f"- {c['text']}{cite}")
            if c.get("calc"):
                out.append(f"  - Calculation: {c['calc']}")
        out.append("")
    return "\n".join(out)


def run(state):
    red = state["privacy"]["redaction"]
    restricted = set(state["privacy"]["restricted_refs"])
    ev_by_ref = {e["ref"]: e for e in state["evidence"]}
    kpis = sorted([k for k in state["kpis"] if k["usable"]],
                  key=lambda k: -Decimal(k["pct_change"] or "0"))
    ok_ev = lambda r: r not in restricted  # noqa: E731
    milestones = [t for t in state["timeline"] if t["type"] == "milestone" and ok_ev(t["ref"])]
    scopes = [s for s in state["scope_changes"] if ok_ev(s["ref"])]
    ctx = next((e for e in state["evidence"] if "context" in e["tags"] and not e["metadata"] and not e.get("row")
                and ok_ev(e["ref"])), None)
    quotes, qnotes = find_quotes(state["evidence"], restricted, red)
    quote = quotes[0] if quotes else None
    span = state.get("span")
    warnings = list(qnotes)
    if not kpis:
        warnings.append("No verified KPIs are available - case studies contain no result claims.")

    def tl(t):
        return _line(f"{t['date']}: {redact(t['text'], red)[0]}", [t["ref"]], "timeline", date=t["date"])

    def sc(s):
        d = f" (dated {s['date']})" if s["date"] else ""
        kind = f" - {s['type']}" if s["type"] != "change" else ""
        return _line(f"Scope change{kind}{d}: {redact(s['text'], red)[0]}", [s["ref"]], "scope",
                     **({"date": s["date"]} if s["date"] else {}))

    note = _line("This case study only contains results that were verified against project evidence.", [], "boilerplate")
    priv = _line("Client identity, personal data and confidential commercial terms are withheld in line with the agreement.",
                 [], "boilerplate")

    # ---- Gatekeeper: governance, scope control, timeline, verified outcomes, data handling
    g = [{"heading": "Overview", "claims": ([_line(redact(ctx["text"], red)[0], [ctx["ref"]], "context")] if ctx else []) + [note]},
         {"heading": "Scope governance", "claims": [sc(s) for s in scopes[:5]]},
         {"heading": "Delivery timeline", "claims": [tl(t) for t in milestones[:6]]},
         {"heading": "Verified outcomes", "claims": [_kpi_claim(k, red) for k in kpis]},
         {"heading": "Data handling", "claims": [priv]}]
    # ---- User: day-to-day impact
    u = [{"heading": "What changed for day-to-day work", "claims": [_kpi_claim(k, red) for k in kpis]},
         {"heading": "In their words", "claims": [_quote_claim(quote)] if quote else []},
         {"heading": "How it was rolled out", "claims": [tl(t) for t in milestones[:3]]},
         {"heading": "About this summary", "claims": [note, priv]}]
    # ---- Buyer: headline result, all results, time-to-value
    top = kpis[0] if kpis else None
    b = [{"heading": "Headline result", "claims": [_kpi_claim(top, red)] if top else []},
         {"heading": "Results at a glance", "claims": [_kpi_claim(k, red) for k in kpis[1:]]},
         {"heading": "Time to value", "claims": ([_line(f"Delivery milestones ran from {span['start']} to {span['end']}.",
                                                       span["refs"], "timeline", calc=span["calc"])] if span else [])},
         {"heading": "Customer voice", "claims": [_quote_claim(quote)] if quote else []},
         {"heading": "About this summary", "claims": [note, priv]}]
    # the Buyer 'span' claim contains two ISO dates: validate with both refs; calc gives the day count
    specs = [("gatekeeper", "Gatekeepers (security, legal, procurement, IT)", "Governance & delivery assurance", g),
             ("user", "Users (people who use the solution)", "What it changed for the people who use it", u),
             ("buyer", "Buyers (economic decision makers)", "Business results", b)]
    versions = []
    for key, aud, title, secs in specs:
        secs = [s for s in secs if s["claims"]]
        v = {"key": key, "audience": aud, "title": title, "sections": secs, "status": "ready_for_review",
             "quote_refs": [c["refs"][0] for s in secs for c in s["claims"] if c["type"] == "quote"]}
        v["markdown"] = _md(v)
        v["grounding"] = validate_version(v, ev_by_ref)
        if not v["grounding"]["ok"]:
            v["status"] = "blocked"
        versions.append(v)
    return ({"versions": versions, "quotes": quotes, "warnings": state.get("warnings", []) + warnings},
            f"3 versions drafted; grounding passed for {sum(v['grounding']['ok'] for v in versions)}/3; {len(quotes)} verified quote(s)")
