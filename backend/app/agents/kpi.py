"""Agent 3 - KPI Verifier: collect claims, recompute results with Decimal, resolve conflicting evidence.

Resolution rule (transparent, shown in the UI):
  authority = source base (xlsx/table 3, pdf 2, docx 2, email 1) +1 if the sentence says final/verified/measured,
              -1 if it says preliminary/estimate/approximately.
  Highest authority wins when all top claims agree; ties that disagree stay UNRESOLVED and are excluded.
"""
import re
from decimal import Decimal

from ..text_utils import fmt_num, parse_number, round1

PATTERN = re.compile(
    r"(?P<verb>reduced|decreased|cut|lowered|dropped|shortened|declined|increased|improved|raised|grew|boosted|lifted|rose)"
    r"\s+(?:the\s+|our\s+|its\s+)?(?P<metric>[A-Za-z][A-Za-z\-/ ]{2,60}?)\s+from\s+"
    r"(?P<a>[$€£]?\d[\d,]*(?:\.\d+)?)\s*(?P<ua>%|[A-Za-z/]+)?\s+to\s+"
    r"(?P<b>[$€£]?\d[\d,]*(?:\.\d+)?)\s*(?P<ub>%|[A-Za-z/]+)?", re.I)
STATED_PCT = re.compile(r"\bby\s+(?:about\s+|roughly\s+|nearly\s+)?(\d+(?:\.\d+)?)\s*%", re.I)
EST_RE = re.compile(r"\b(preliminary|estimate[ds]?|draft|projected|approximately|approx\.?|forecast|roughly)\b", re.I)
FINAL_RE = re.compile(r"\b(final|verified|audited|signed[- ]off|measured|confirmed|validated)\b", re.I)
STOP = {"the", "our", "its", "average", "avg", "mean", "overall"}
BASE_AUTH = {"xlsx": 3, "table": 3, "pdf": 2, "docx": 2, "eml": 1}


def metric_key(name: str) -> str:
    n = re.sub(r"\(.*?\)", " ", name.lower())
    words = [w for w in re.split(r"\s+", n.strip()) if w and w not in STOP]
    if words and len(words[-1]) > 4 and words[-1].endswith("s") and not words[-1].endswith("ss"):
        words[-1] = words[-1][:-1]
    return " ".join(words)


def _unit(tok):
    tok = (tok or "").strip()
    return tok if tok in ("%", "$", "€", "£") or (tok and tok.lower() not in ("to", "by", "and", "in", "with")) else ""


def _authority(ev, text):
    base = BASE_AUTH.get("table" if ev.get("kind_hint") == "table" else ev["doc_kind"], 1)
    est = bool(EST_RE.search(text))
    return base + (1 if FINAL_RE.search(text) else 0) - (1 if est else 0), est


def _claims(evidence):
    out = []
    for ev in evidence:
        if ev["metadata"]:
            continue
        if ev.get("row"):
            row = {k.lower().strip(): (k, v) for k, v in ev["row"].items()}
            find = lambda *names: next((row[k][1] for k in row if any(n in k for n in names)), None)  # noqa: E731
            name, base, res = find("kpi", "metric", "measure", "indicator"), find("baseline", "before"), find("result", "actual", "after", "achieved", "current")
            a, b = parse_number(base), parse_number(res)
            if not name or a is None or b is None:
                continue
            unit = (find("unit") or "").strip()
            m = re.search(r"\((.*?)\)", name)
            unit = unit or (m.group(1) if m else "")
            auth, est = _authority(ev, ev["text"])
            out.append({"name": re.sub(r"\(.*?\)", "", name).strip(), "unit": unit, "a": a, "b": b, "ref": ev["ref"],
                        "authority": auth, "estimate": est, "stated_pct": None})
            continue
        for m in PATTERN.finditer(ev["text"]):
            a, b = parse_number(m.group("a")), parse_number(m.group("b"))
            unit = _unit(m.group("ub")) or _unit(m.group("ua"))
            if not unit and m.group("a")[0] in "$€£":
                unit = m.group("a")[0]
            auth, est = _authority(ev, ev["text"])
            sp = STATED_PCT.search(ev["text"])
            out.append({"name": m.group("metric").strip(), "unit": unit, "a": a, "b": b, "ref": ev["ref"],
                        "authority": auth, "estimate": est, "stated_pct": Decimal(sp.group(1)) if sp else None})
    return out


def _same(c1, c2):
    close = lambda x, y: abs(x - y) <= max(abs(x), abs(y)) * Decimal("0.005")  # noqa: E731
    return close(c1["a"], c2["a"]) and close(c1["b"], c2["b"])


def calculate(a: Decimal, b: Decimal, unit: str):
    change = b - a
    direction = "decreased" if change < 0 else "increased" if change > 0 else "was unchanged"
    noun = "reduction" if change < 0 else "increase" if change > 0 else "change"
    if a == 0:
        return change, None, direction, noun, f"baseline is 0, percent change undefined ({fmt_num(b)} - {fmt_num(a)} = {fmt_num(change)})"
    pct = round1(abs(change) / abs(a) * 100)
    calc = f"({fmt_num(a)} - {fmt_num(b)}) / {fmt_num(a)} x 100 = {pct}% {noun}" if change < 0 else \
           f"({fmt_num(b)} - {fmt_num(a)}) / {fmt_num(a)} x 100 = {pct}% {noun}"
    return change, pct, direction, noun, calc


def run(state):
    groups = {}
    for c in _claims(state["evidence"]):
        groups.setdefault(metric_key(c["name"]), []).append(c)
    ev_doc = {e["ref"]: e["doc"] for e in state["evidence"]}
    kpis = []
    for i, (key, cl) in enumerate(sorted(groups.items()), start=1):
        cl.sort(key=lambda c: -c["authority"])
        top = [c for c in cl if c["authority"] == cl[0]["authority"]]
        chosen, warnings, rationale = cl[0], [], ""
        agree = all(_same(top[0], c) for c in top)
        support = [c for c in cl if _same(chosen, c)]
        others = [c for c in cl if not _same(chosen, c)]
        if not agree:
            status = "unresolved"
            rationale = "Sources of equal authority disagree: " + "; ".join(
                f"{c['ref']} says {fmt_num(c['a'])} -> {fmt_num(c['b'])}" for c in top)
        elif chosen["estimate"]:
            status, rationale = "estimate_only", "Only estimates/preliminary figures exist; they cannot be published as results."
        elif others:
            status = "conflict_resolved"
            rationale = (f"{chosen['ref']} (authority {chosen['authority']}) outranks " +
                         ", ".join(f"{c['ref']} (authority {c['authority']})" for c in others) + ".")
        else:
            status = "verified"
        change, pct, direction, noun, calc = calculate(chosen["a"], chosen["b"], chosen["unit"])
        for c in cl:
            if c["stated_pct"] is not None and pct is not None:
                cp = round1(abs(c["b"] - c["a"]) / abs(c["a"]) * 100) if c["a"] else None
                if cp is not None and abs(cp - c["stated_pct"]) > Decimal("0.6"):
                    warnings.append(f"{c['ref']} states {c['stated_pct']}% but the recalculated change is {cp}% - the recalculated value is used.")
        if status in ("verified", "conflict_resolved") and len({ev_doc[c['ref']] for c in support}) == 1 and len(support) == 1:
            warnings.append("Single source - no independent corroboration.")
        kpis.append({
            "id": f"K{i}", "key": key, "kpi": chosen["name"][:1].upper() + chosen["name"][1:], "unit": chosen["unit"],
            "baseline": str(chosen["a"]), "result": str(chosen["b"]), "change": str(change),
            "pct_change": str(pct) if pct is not None else None, "direction": direction, "noun": noun,
            "calc": calc, "status": status, "chosen_ref": chosen["ref"],
            "refs": [c["ref"] for c in support], "overridden": [
                {"ref": c["ref"], "baseline": str(c["a"]), "result": str(c["b"]), "authority": c["authority"]} for c in others],
            "rationale": rationale, "warnings": warnings, "needs_review": bool(warnings) or status != "verified",
            "usable": status in ("verified", "conflict_resolved"), "privacy_blocked": False})
    n_ok = sum(k["usable"] for k in kpis)
    return {"kpis": kpis}, f"{len(kpis)} KPI(s) found: {n_ok} verified, {len(kpis) - n_ok} excluded"
