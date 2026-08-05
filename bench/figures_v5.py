#!/usr/bin/env python3
"""Figures for draft 5. Each answers one question a reader would actually ask."""
from __future__ import annotations
import json, pathlib, statistics as st
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = (pathlib.Path.home() / "Documents/ludo-claude/ludo-writting-workshop"
       "/writting-projects/papers/2026/mcp-vs-cli-benchmark/figures")

# Categorical hues assigned by role, fixed order, never cycled.
CLI   = "#2a6fdb"   # shell-only arm
MCP   = "#e2622a"   # catalogue arm
MIN   = "#1f9d63"   # minimal scaffolding (no MCP client)
INK, MUTED, SURF, GRID = "#111111", "#575757", "#ffffff", "#dcdcdc"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10})

ORDER = ["pi", "tau", "hermes", "codex", "qwen-code", "claude-code"]
MINIMAL = {"pi", "tau"}


def load():
    return [json.loads(l) for l in (ROOT / "results/e3-final.jsonl").read_text().splitlines() if l.strip()]


def live(rows):
    return [r for r in rows if not r.get("void") and r.get("total_input_tokens")]


def _style(ax, title, ylabel="", xlabel=""):
    ax.set_facecolor(SURF); ax.figure.set_facecolor(SURF)
    ax.set_title(title, color=INK, fontsize=10, loc="left", pad=8)
    if ylabel: ax.set_ylabel(ylabel, color=MUTED)
    if xlabel: ax.set_xlabel(xlabel, color=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.7, zorder=0); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", facecolor=SURF, bbox_inches="tight", dpi=200)
    plt.close(fig); print("  ", name)


def fig1_scaffolding(rows):
    """The headline: cost spans 31x across harnesses, and the cheap ones never fail."""
    d = defaultdict(list)
    for r in live(rows): d[r["scaffolding"]].append(r)
    names = [s for s in ORDER if s in d]
    med = [st.median(x["total_input_tokens"] for x in d[s]) for s in names]
    comp = [100*sum(1 for x in d[s] if (x.get("completion_pct") or 0)==100)/len(d[s]) for s in names]
    cols = [MIN if s in MINIMAL else MCP for s in names]

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.5), dpi=200)
    b = a1.barh(range(len(names)), med, color=cols, height=.62, lw=0)
    for i, (bb, v) in enumerate(zip(b, med)):
        a1.text(v*1.06, i, f"{v:,.0f}", va="center", fontsize=8.5, color=INK)
    a1.set_xscale("log"); a1.set_yticks(range(len(names)))
    a1.set_yticklabels(names, color=INK); a1.invert_yaxis()
    a1.set_xlim(right=max(med)*3)
    _style(a1, "Median tokens per run  (log scale)", xlabel="input tokens")
    a1.grid(axis="y", visible=False); a1.grid(axis="x", color=GRID, lw=.7)

    b2 = a2.barh(range(len(names)), comp, color=cols, height=.62, lw=0)
    for i, v in enumerate(comp):
        a2.text(v+2, i, f"{v:.0f}%", va="center", fontsize=8.5, color=INK)
    a2.set_yticks(range(len(names))); a2.set_yticklabels(names, color=INK)
    a2.invert_yaxis(); a2.set_xlim(0, 118)
    _style(a2, "Runs completing the whole task", xlabel="% of runs")
    a2.grid(axis="y", visible=False); a2.grid(axis="x", color=GRID, lw=.7)

    h = [plt.Rectangle((0,0),1,1,color=MIN), plt.Rectangle((0,0),1,1,color=MCP)]
    lg = fig.legend(h, ["no MCP client (minimal)", "MCP-capable"], frameon=False,
                    ncol=2, loc="lower center", bbox_to_anchor=(.5,-.06), fontsize=8.5)
    for t in lg.get_texts(): t.set_color(MUTED)
    fig.tight_layout(); save(fig, "v5-scaffolding")


def fig2_arms(rows):
    """Within each MCP-capable harness: what does attaching the catalogue cost?

    Completion is shown beside every bar because a ratio is only interpretable
    when both arms finished the task; a cheap arm that failed is not a saving.
    """
    d = defaultdict(dict)
    for r in live(rows): d[r["scaffolding"]].setdefault(r["arm"], []).append(r)
    names = [s for s in ORDER if "mcp" in d.get(s, {}) and "cli" in d.get(s, {})]

    def med(s, a): return st.median(x["total_input_tokens"] for x in d[s][a])
    def don(s, a):
        rs = d[s][a]
        return sum(1 for x in rs if (x.get("completion_pct") or 0) == 100), len(rs)

    cli = [med(s, "cli") for s in names]
    mcp = [med(s, "mcp") for s in names]

    fig, ax = plt.subplots(figsize=(7.8, 3.5), dpi=200)
    y = range(len(names)); h = .34
    ax.barh([i+h/2 for i in y], cli, height=h, color=CLI, lw=0, label="shell only")
    ax.barh([i-h/2 for i in y], mcp, height=h, color=MCP, lw=0, label="catalogue attached")
    top = max(max(cli), max(mcp))
    for i, s in enumerate(names):
        c, m = cli[i], mcp[i]
        cd, cn = don(s, "cli"); md, mn = don(s, "mcp")
        ax.text(c*1.05, i+h/2, f"{c:,.0f}   {cd}/{cn} done", va="center",
                fontsize=8, color=INK)
        ax.text(m*1.05, i-h/2, f"{m:,.0f}   {md}/{mn} done", va="center",
                fontsize=8, color=INK)
        both = (cd == cn) and (md == mn)
        ax.text(top*3.6, i, f"×{m/c:.2f}", va="center", ha="right", fontsize=9.5,
                color=INK if both else MUTED,
                fontweight="bold" if both else "normal")
    ax.text(top*3.6, -0.8, "catalogue ÷ shell", va="center", ha="right",
            fontsize=8, color=MUTED)
    ax.set_xscale("log"); ax.set_yticks(list(y)); ax.set_yticklabels(names, color=INK)
    ax.invert_yaxis(); ax.set_xlim(right=top*4.2)
    _style(ax, "Cost of attaching a tool catalogue, within each harness",
           xlabel="median input tokens (log scale)")
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color=GRID, lw=.7)
    lg = fig.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower center",
                    bbox_to_anchor=(.5, -.05))
    for t in lg.get_texts(): t.set_color(MUTED)
    fig.tight_layout(); save(fig, "v5-arms")


def fig3_catalogue(rows):
    """The mechanism: what the catalogue costs depends on how it is delivered.

    Hermes reaches the same 44-tool GitHub server through a gateway — it ships
    seven schemas per request and fetches definitions on demand. The others
    ship all 44 on every turn. Same server, same task, different bill.
    """
    KNOWN_INLINE = {"codex": 44, "qwen-code": 44, "claude-code": 44}
    groups = {"on demand\n(7 schemas/request)": [], "shipped inline\n(44 schemas/request)": []}
    for r in live(rows):
        if r["arm"] != "mcp":
            continue
        n = r.get("catalogue_size") or KNOWN_INLINE.get(r["scaffolding"])
        if not n:
            continue
        key = list(groups)[0] if n <= 10 else list(groups)[1]
        groups[key].append((r["scaffolding"], r["total_input_tokens"]))
    labels = [k for k in groups if groups[k]]
    if len(labels) < 2:
        return

    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=200)
    tick_extra = {}
    for i, k in enumerate(labels):
        vals = [v for _, v in groups[k]]
        m = st.median(vals)
        colour = MIN if i == 0 else MCP
        ax.bar(i, m, width=.5, color=colour, lw=0, zorder=2)
        ax.text(i, m*1.08, f"median {m:,.0f}", ha="center", fontsize=9,
                color=INK, fontweight="bold")
        # Individual runs as dots; naming each one collides at this density and
        # the group already carries the identity that matters.
        for _, v in groups[k]:
            ax.scatter(i + 0.34, v, s=40, color="white", edgecolor=colour,
                       lw=1.6, zorder=4)
        harnesses = sorted({n for n, _ in groups[k]})
        tick_extra[k] = f"\n{', '.join(harnesses)}  ({len(vals)} runs)"
    ax.set_yscale("log")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([k + tick_extra.get(k, "") for k in labels], color=INK,
                       fontsize=8.5)
    ax.set_xlim(-.55, len(labels) - .1)
    _style(ax, "Same MCP server, two delivery modes — catalogue arms only",
           ylabel="input tokens (log scale)")
    ax.grid(axis="y", color=GRID, lw=.7)
    fig.tight_layout(); save(fig, "v5-catalogue")


def tables(rows):
    out = ["| Harness | MCP client | Runs | Median tokens | Relative | Completed |",
           "|---|:--:|---:|---:|---:|---:|"]
    d = defaultdict(list)
    for r in live(rows): d[r["scaffolding"]].append(r)
    names = sorted(d, key=lambda s: st.median(x["total_input_tokens"] for x in d[s]))
    base = st.median(x["total_input_tokens"] for x in d[names[0]])
    for s in names:
        m = st.median(x["total_input_tokens"] for x in d[s])
        done = sum(1 for x in d[s] if (x.get("completion_pct") or 0) == 100)
        out.append(f"| {s} | {'no' if s in MINIMAL else 'yes'} | {len(d[s])} | "
                   f"{m:,.0f} | ×{m/base:.1f} | {done}/{len(d[s])} |")
    t1 = "\n".join(out)

    out = ["| Harness | Model | Arm | Tokens | Cache | Calls | Offered | Completed |",
           "|---|---|:--:|---:|---:|---:|---:|---:|"]
    for r in sorted(rows, key=lambda r: (r["scaffolding"], r["model"], r["arm"])):
        if r.get("void"):
            out.append(f"| {r['scaffolding']} | {r['model']} | {r['arm']} | void | | | | "
                       f"{(r.get('void_reason') or '')[:28]} |")
            continue
        f = lambda v: "—" if v in (None, 0) else f"{v:,}"
        ch = r.get("cache_hit_pct")
        out.append(f"| {r['scaffolding']} | {r['model']} | {r['arm']} | "
                   f"{f(r.get('total_input_tokens'))} | {'—' if ch is None else f'{ch:.0f}%'} | "
                   f"{f(r.get('tool_calls'))} | {f(r.get('catalogue_size'))} | "
                   f"{r.get('completion_pct')}% |")
    (ROOT / "results/tables-v5.md").write_text(t1 + "\n\n" + "\n".join(out) + "\n")
    print("   tables-v5.md")


if __name__ == "__main__":
    rows = load()
    fig1_scaffolding(rows); fig2_arms(rows); fig3_catalogue(rows); tables(rows)
