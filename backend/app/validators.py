"""Grounding validator: every claim must cite evidence, and every number/date/quote in it must be traceable."""
import re

from .text_utils import ISO_RE, REF_RE, numbers_in
from .agents.timeline import find_dates


def validate_claim(claim: dict, ev_by_ref: dict) -> list:
    issues = []
    refs = claim.get("refs") or []
    if not refs:
        return ["claim has no evidence reference"]
    missing = [r for r in refs if r not in ev_by_ref]
    if missing:
        return [f"unknown evidence reference(s): {', '.join(missing)}"]
    allowed = set()
    for r in refs:
        allowed |= numbers_in(ev_by_ref[r]["text"])
    allowed |= numbers_in(ISO_RE.sub(" ", claim.get("calc") or ""))
    body = ISO_RE.sub(" ", REF_RE.sub(" ", claim["text"]))
    extra = numbers_in(body) - allowed
    if extra:
        issues.append(f"numbers not found in cited evidence or calculation: {sorted(extra)}")
    if claim.get("date"):
        ok = any(claim["date"] in {d.isoformat() for d in find_dates(ev_by_ref[r]["text"])} or ev_by_ref[r].get("date") == claim["date"]
                 for r in refs)
        if not ok:
            issues.append(f"date {claim['date']} not found in cited evidence")
    if claim.get("quote") and claim["quote"] not in ev_by_ref[refs[0]]["text"]:
        issues.append("quote is not verbatim in the cited evidence")
    return issues


def validate_version(version: dict, ev_by_ref: dict) -> dict:
    issues = []
    n = 0
    for sec in version["sections"]:
        for c in sec["claims"]:
            if c["type"] == "boilerplate":
                continue
            n += 1
            for i in validate_claim(c, ev_by_ref):
                issues.append({"section": sec["heading"], "claim": c["text"][:80], "issue": i})
    return {"ok": not issues, "claims_checked": n, "issues": issues}
