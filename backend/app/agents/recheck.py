"""Agent 6 - Privacy Re-check: scan every generated version again; block anything that still leaks."""
from .privacy import scan


def run(state):
    red = state["privacy"]["redaction"]
    leaks_total = []
    for v in state["versions"]:
        leaks = scan(v["markdown"], red)
        v["privacy_recheck"] = {"passed": not leaks, "leaks": [f"{k}: {m}" for k, m in leaks]}
        if leaks:
            v["status"] = "blocked"
            leaks_total += leaks
    privacy = dict(state["privacy"])
    privacy["recheck"] = {"passed": not leaks_total, "leak_count": len(leaks_total)}
    return {"versions": state["versions"], "privacy": privacy}, \
        "Re-check passed - no leaks found" if not leaks_total else f"{len(leaks_total)} leak(s) found - versions blocked"
