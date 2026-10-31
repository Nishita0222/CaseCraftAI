"""Agent 2 - Timeline & Scope: dates stated in the evidence -> timeline; scope-change detection."""
import re
from datetime import date

from .common import MILESTONE_RE, SCOPE_RE
from ..text_utils import ISO_RE

_MON = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MN = r"(Jan[a-z]*|Feb[a-z]*|Mar[a-z]*|Apr[a-z]*|May|Jun[a-z]*|Jul[a-z]*|Aug[a-z]*|Sep[a-z]*|Oct[a-z]*|Nov[a-z]*|Dec[a-z]*)"
DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MN}\.?,?\s+(\d{{4}})\b", re.I)
MDY = re.compile(rf"\b{_MN}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I)


def _mk(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def find_dates(text: str) -> list:
    found = []
    for m in ISO_RE.finditer(text):
        found.append((m.start(), _mk(*m.group(0).split("-"))))
    for m in DMY.finditer(text):
        found.append((m.start(), _mk(m.group(3), _MON[m.group(2)[:3].lower()], m.group(1))))
    for m in MDY.finditer(text):
        found.append((m.start(), _mk(m.group(3), _MON[m.group(1)[:3].lower()], m.group(2))))
    return [d for _, d in sorted(found, key=lambda x: x[0]) if d]


def _scope_type(t: str) -> str:
    t = t.lower()
    if re.search(r"de-?scop|out of scope|removed|dropped", t):
        return "reduction"
    if re.search(r"extend|extension|delay|postpone|reschedul", t):
        return "schedule change"
    if re.search(r"add|additional|new requirement|expanded", t):
        return "addition"
    return "change"


def run(state):
    events, undated, scope = [], [], []
    seen = set()
    for e in state["evidence"]:
        if e["metadata"] or e.get("row"):
            continue
        txt = e["text"]
        is_scope, is_ms = bool(SCOPE_RE.search(txt)), bool(MILESTONE_RE.search(txt))
        if not (is_scope or is_ms):
            continue
        dates = find_dates(txt)
        d = dates[0].isoformat() if dates else None
        if is_scope:
            scope.append({"ref": e["ref"], "doc": e["doc"], "location": e["location"], "text": txt,
                          "type": _scope_type(txt), "date": d, "communicated": e.get("date")})
        if d:
            key = (d, txt)
            if key not in seen:
                seen.add(key)
                events.append({"date": d, "type": "scope" if is_scope else "milestone", "text": txt, "ref": e["ref"],
                               "doc": e["doc"], "location": e["location"],
                               "note": "multiple dates in sentence; first used" if len(dates) > 1 else ""})
        else:
            undated.append({"type": "scope" if is_scope else "milestone", "text": txt, "ref": e["ref"],
                            "doc": e["doc"], "location": e["location"]})
    events.sort(key=lambda x: x["date"])
    span = None
    ms = [x for x in events if x["type"] == "milestone"]
    if len(ms) >= 2:
        a, b = ms[0], ms[-1]
        days = (date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days
        span = {"start": a["date"], "end": b["date"], "days": days, "refs": [a["ref"], b["ref"]],
                "calc": f"{b['date']} - {a['date']} = {days} days"}
    return ({"timeline": events, "undated": undated, "scope_changes": scope, "span": span},
            f"{len(events)} dated events, {len(scope)} scope change(s), {len(undated)} undated item(s)")
