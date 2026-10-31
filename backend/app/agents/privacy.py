"""Agent 4 - Privacy Guard: PII, client identity, NDA clauses, financial terms -> redaction rules."""
import re

from .common import NDA_RE, QUOTE_VERB

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{3,4}(?!\d)")
AMOUNT_RE = re.compile(r"[$€£]\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|bn|million|billion)?\b", re.I)
FIN_CONTEXT = re.compile(r"\b(contract|fee|fees|price|pricing|budget|invoice|retainer|licen[cs]e|purchase order)\b|cost of", re.I)
PERSON_AFTER_VERB = re.compile(rf"\b{QUOTE_VERB}\s+((?:[A-Z][a-z]+)(?:\s[A-Z][a-z]+)+)")
TITLE_NAME = re.compile(r"\b(?:Mr|Ms|Mrs|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s[A-Z][a-z]+)?")


def phones_in(text):
    return [m.group(0).strip() for m in PHONE_RE.finditer(text) if 10 <= len(re.sub(r"\D", "", m.group(0))) <= 13]


def client_variants(client_name: str) -> list:
    name = (client_name or "").strip()
    if not name:
        return []
    out = {name}
    first = name.split()[0]
    if len(name.split()) > 1 and len(first) >= 4:
        out.add(first)
    return sorted(out, key=len, reverse=True)


def redact(text: str, red: dict):
    """Apply redactions. Returns (new_text, [labels of what was removed])."""
    changes = []

    def sub(pattern, repl, label, t):
        new, n = pattern.subn(repl, t)
        if n:
            changes.append(label)
        return new

    text = sub(EMAIL_RE, "[email removed]", "email", text)
    text = PHONE_RE.sub(lambda m: "[phone removed]" if 10 <= len(re.sub(r"\D", "", m.group(0))) <= 13 else m.group(0), text)
    if "[phone removed]" in text:
        changes.append("phone")
    for p in sorted(red.get("people", []), key=len, reverse=True):
        text = sub(re.compile(re.escape(p), re.I), "[name withheld]", "person", text)
    for t in sorted(red.get("terms", []), key=len, reverse=True):
        text = sub(re.compile(re.escape(t), re.I), "[redacted]", "confidential term", text)
    for v in red.get("client_variants", []):
        text = sub(re.compile(rf"\b{re.escape(v)}\b", re.I), "the client", "client name", text)
    return text, sorted(set(changes))


def scan(text: str, red: dict) -> list:
    """Return a list of leaks still present in `text` (used for the post-generation re-check)."""
    leaks = [("email", m.group(0)) for m in EMAIL_RE.finditer(text)]
    leaks += [("phone", p) for p in phones_in(text)]
    for kind, items in (("person", red.get("people", [])), ("confidential term", red.get("terms", [])),
                        ("client name", red.get("client_variants", []))):
        for it in items:
            if re.search(rf"\b{re.escape(it)}\b", text, re.I):
                leaks.append((kind, it))
    return leaks


def run(state):
    project = state["project"]
    terms = [t.strip() for t in (project.get("confidential_terms") or "").split(",") if t.strip()]
    red = {"client_variants": client_variants(project.get("client_name")), "terms": terms, "people": []}
    findings, restricted, nda_texts = [], {}, []

    def add(e, ftype, match, action, severity, note=""):
        findings.append({"id": f"P{len(findings) + 1}", "ref": e["ref"], "doc": e["doc"], "location": e["location"],
                         "type": ftype, "match": match, "action": action, "severity": severity, "note": note})

    for e in state["evidence"]:
        t = e["text"]
        for p in e.get("people", []):
            if p not in red["people"]:
                red["people"].append(p)
        for m in EMAIL_RE.finditer(t):
            add(e, "email", m.group(0), "redact", "medium")
        for p in phones_in(t):
            add(e, "phone", p, "redact", "medium")
        for m in list(PERSON_AFTER_VERB.finditer(t)) + list(TITLE_NAME.finditer(t)):
            name = m.group(1) if m.re is PERSON_AFTER_VERB else m.group(0)
            if name not in red["people"]:
                red["people"].append(name)
            add(e, "person_name", name, "redact", "medium")
        for v in red["client_variants"]:
            if re.search(rf"\b{re.escape(v)}\b", t, re.I):
                add(e, "client_name", v, "anonymize", "high", "client is never named unless approved")
                break
        for term in terms:
            if re.search(re.escape(term), t, re.I):
                add(e, "confidential_term", term, "redact", "high")
        if not e["metadata"]:
            if NDA_RE.search(t):
                add(e, "nda_clause", NDA_RE.search(t).group(0), "restrict", "high", "sentence is never used in outputs")
                restricted.setdefault(e["ref"], []).append("NDA / confidentiality clause")
                nda_texts.append(t.lower())
            if AMOUNT_RE.search(t) and FIN_CONTEXT.search(t):
                add(e, "financial_terms", AMOUNT_RE.search(t).group(0), "restrict", "high", "commercial terms are withheld")
                restricted.setdefault(e["ref"], []).append("commercial / financial terms")
    # an NDA clause that talks about a KPI blocks that KPI from publication
    for k in state.get("kpis", []):
        toks = [w for w in k["key"].split() if len(w) > 3]
        for nt in nda_texts:
            if k["key"] in nt or (toks and sum(w in nt for w in toks) >= min(2, len(toks))):
                k["privacy_blocked"], k["usable"] = True, False
                k["status"] = "privacy_blocked"
                k["rationale"] = "An NDA / confidentiality clause refers to this KPI - excluded until the client approves."
                break
        if any(r in restricted for r in k["refs"]):
            k["privacy_blocked"], k["usable"], k["status"] = True, False, "privacy_blocked"
            k["rationale"] = "Source sentence is restricted by an NDA / confidentiality marker."
    counts = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    privacy = {
        "findings": findings, "counts": counts, "restricted": restricted, "restricted_refs": sorted(restricted),
        "redaction": red,
        "rules": ["Client identity is anonymized in every output ('the client').",
                  "Emails, phone numbers and personal names are removed.",
                  "Sentences containing NDA / confidentiality markers are never quoted.",
                  "Contract, price and fee amounts are withheld.",
                  "KPIs touched by an NDA clause are blocked until the client approves them.",
                  "Every generated output is re-scanned for leaks before approval."]}
    return ({"privacy": privacy, "kpis": state.get("kpis", [])},
            f"{len(findings)} privacy finding(s); {len(restricted)} sentence(s) restricted; "
            f"{sum(k['privacy_blocked'] for k in state.get('kpis', []))} KPI(s) blocked")
