"""Agent 7 - Media Studio: charts / timeline / infographic / quote card, drawn only from verified data."""
import textwrap
from decimal import Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ..text_utils import fmt_val  # noqa: E402
from .privacy import redact, scan  # noqa: E402

NAVY, TEAL, GREY, SLATE = "#0f172a", "#0f766e", "#94a3b8", "#475569"


def _footer(fig, refs, project):
    synth = "SYNTHETIC DEMO DATA  |  " if project.get("synthetic") else ""
    fig.text(0.5, 0.012, f"{synth}Sources: {', '.join(refs)}  |  Calculations in the approval pack", ha="center",
             fontsize=7.5, color=SLATE)


def _wrap(t, w):
    return "\n".join(textwrap.wrap(t, w)) or t


def run(state):
    project, red = state["project"], state["privacy"]["redaction"]
    out = Path(state["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    kpis = sorted([k for k in state["kpis"] if k["usable"]], key=lambda k: -Decimal(k["pct_change"] or "0"))
    assets, warnings = [], []

    def save(fig, name, typ, caption, alt, refs, texts):
        p = out / name
        fig.savefig(p, dpi=150, facecolor="white")
        plt.close(fig)
        leaks = scan(" ".join(texts), red)
        assets.append({"name": name, "type": typ, "path": str(p), "caption": caption, "alt": alt, "refs": refs,
                       "status": "blocked" if leaks else "ready_for_review",
                       "privacy_recheck": {"passed": not leaks, "leaks": [f"{k}: {m}" for k, m in leaks]}})

    if kpis:
        shown = kpis[:4]
        fig, axes = plt.subplots(1, len(shown), figsize=(3.6 * len(shown) + 0.6, 4.6))
        axes = [axes] if len(shown) == 1 else list(axes)
        texts, refs = [], []
        for ax, k in zip(axes, shown):
            a, b = float(Decimal(k["baseline"])), float(Decimal(k["result"]))
            ax.bar(["Baseline", "Result"], [a, b], color=[GREY, TEAL], width=0.6)
            ax.set_ylim(0, max(a, b) * 1.3 or 1)
            for x, val in enumerate((Decimal(k["baseline"]), Decimal(k["result"]))):
                ax.text(x, [a, b][x], fmt_val(val, k["unit"]), ha="center", va="bottom", fontsize=9, color=NAVY)
            title = redact(k["kpi"], red)[0]
            ax.set_title(_wrap(title, 22), fontsize=10, color=NAVY)
            sub = f"{k['pct_change']}% {k['noun']}" if k["pct_change"] else ""
            ax.set_xlabel(sub, fontsize=9, color=TEAL)
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
            texts += [title, sub]
            refs += k["refs"]
        fig.suptitle("Verified KPI results", fontsize=13, color=NAVY, fontweight="bold")
        fig.tight_layout(rect=(0, 0.05, 1, 0.94))
        refs = sorted(set(refs))
        _footer(fig, refs, project)
        save(fig, "kpi_results_chart.png", "chart", "Baseline versus result for each verified KPI.",
             "Bar chart comparing baseline and result for verified KPIs.", refs, texts)

        top = kpis[0]
        fig = plt.figure(figsize=(8, 4.5))
        fig.patch.set_facecolor(NAVY)
        title = redact(top["kpi"], red)[0]
        fig.text(0.07, 0.80, "HEADLINE RESULT", color="#5eead4", fontsize=11, fontweight="bold")
        fig.text(0.07, 0.50, f"{top['pct_change']}%" if top["pct_change"] else "n/a", color="white", fontsize=64,
                 fontweight="bold")
        fig.text(0.07, 0.38, f"{top['noun']} in {title.lower()}", color="white", fontsize=16)
        fig.text(0.07, 0.28, f"{fmt_val(Decimal(top['baseline']), top['unit'])}  →  {fmt_val(Decimal(top['result']), top['unit'])}",
                 color="#99f6e4", fontsize=14)
        fig.text(0.07, 0.17, "Calc: " + top["calc"].replace("x", "×"), color="#94a3b8", fontsize=8.5)
        synth = "SYNTHETIC DEMO DATA  |  " if project.get("synthetic") else ""
        fig.text(0.07, 0.06, f"{synth}Sources: {', '.join(top['refs'])}", color="#94a3b8", fontsize=8)
        save(fig, "headline_infographic.png", "infographic", "Headline KPI with its calculation.",
             f"Infographic: {top['pct_change']}% {top['noun']} in {title}.", top["refs"],
             [title, top["calc"], top["noun"]])
    else:
        warnings.append("Media: no verified KPIs, so KPI chart and infographic were not created.")

    events = [t for t in state["timeline"]][:8]
    if len(events) >= 2:
        fig, ax = plt.subplots(figsize=(11, 4.2))
        ax.axhline(0, color=GREY, lw=2)
        texts = []
        for i, ev in enumerate(events):
            y = 1 if i % 2 == 0 else -1
            label = redact(ev["text"], red)[0]
            label = label if len(label) <= 70 else label[:67] + "..."
            ax.plot([i, i], [0, 0.6 * y], color=TEAL, lw=1)
            ax.scatter([i], [0], color=TEAL, zorder=3)
            ax.text(i, 0.68 * y, f"{ev['date']}\n{_wrap(label, 24)}", ha="center", va="bottom" if y > 0 else "top",
                    fontsize=7.5, color=NAVY)
            texts.append(label)
        ax.set_ylim(-2.4, 2.4)
        ax.set_xlim(-0.8, len(events) - 0.2)
        ax.axis("off")
        ax.set_title("Project timeline (dates as stated in project documents)", fontsize=12, color=NAVY)
        refs = [e["ref"] for e in events]
        _footer(fig, refs, project)
        save(fig, "project_timeline.png", "timeline", "Timeline of dated milestones and scope changes.",
             "Horizontal timeline of dated project milestones.", refs, texts)
    else:
        warnings.append("Media: fewer than two dated events, timeline graphic skipped.")

    if state.get("quotes"):
        q = state["quotes"][0]
        fig = plt.figure(figsize=(8, 4.5))
        fig.patch.set_facecolor("#f0fdfa")
        fig.text(0.06, 0.76, "“", fontsize=70, color=TEAL)
        fig.text(0.12, 0.52, _wrap(q["quote"], 48), fontsize=15, color=NAVY, va="center")
        fig.text(0.12, 0.18, f"— {q['attribution']}", fontsize=12, color=SLATE)
        fig.text(0.12, 0.06, f"Verbatim from {q['ref']}. Requires written client consent before use.", fontsize=8, color=SLATE)
        save(fig, "quote_card.png", "quote_card", "Verbatim client quote (consent required).",
             f"Quote card: {q['quote'][:60]}", [q["ref"]], [q["quote"], q["attribution"]])
    if len(assets) < 3:
        warnings.append(f"Only {len(assets)} media asset(s) could be created from verified evidence (3 required) - add more evidence.")
    return ({"assets": assets, "warnings": state.get("warnings", []) + warnings},
            f"{len(assets)} media asset(s) created")
