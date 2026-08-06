#!/usr/bin/env python3
"""Figures for draft 8, conditioned exactly as Section 2.8 prescribes.

The v5 figures predate the conditioning rule and plot pooled medians; draft 7
shipped them beside completed-only tables, so figure and table disagreed on the
same page. Everything here is computed over completed runs, with completion
shown separately over attempts — the same split the tables use.
"""
from __future__ import annotations
import json, pathlib, statistics as st
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = (pathlib.Path.home() / "Documents/ludo-claude/ludo-writting-workshop"
       "/writting-projects/papers/2026/mcp-vs-cli-benchmark/figures")
CLI, MCP, MIN = "#2a6fdb", "#e2622a", "#1f9d63"
INK, MUTED, SURF, GRID = "#111111", "#575757", "#ffffff", "#dcdcdc"
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10})
ORDER = ["pi", "tau", "hermes", "codex", "qwen-code", "claude-code"]
MINIMAL = {"pi", "tau"}
DISP = {"pi": "pi", "tau": "Tau", "hermes": "Hermes", "codex": "Codex",
        "qwen-code": "qwen-code", "claude-code": "Claude Code"}


def load():
    rows = [json.loads(l) for l in (ROOT / "results/e3-final.jsonl").read_text().splitlines() if l.strip()]
    live = [r for r in rows if not r.get("void") and r.get("total_input_tokens")]
    done = [r for r in live if (r.get("completion_pct") or 0) == 100]
    return live, done


def _style(ax, title, ylabel="", xlabel=""):
    ax.set_facecolor(SURF); ax.figure.set_facecolor(SURF)
    ax.set_title(title, color=INK, fontsize=10, loc="left", pad=8)
    if ylabel: ax.set_ylabel(ylabel, color=MUTED)
    if xlabel: ax.set_xlabel(xlabel, color=MUTED)
    ax.grid(axis="y", color=GRID, lw=.7, zorder=0); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", facecolor=SURF, bbox_inches="tight", dpi=200)
    plt.close(fig); print("  ", name)


def fig_scaffolding(live, done):
    a, b = defaultdict(list), defaultdict(list)
    for r in live: a[r["scaffolding"]].append(r)
    for r in done: b[r["scaffolding"]].append(r)
    names = [s for s in ORDER if s in b]
    names.sort(key=lambda s: st.median(x["total_input_tokens"] for x in b[s]))
    med = [st.median(x["total_input_tokens"] for x in b[s]) for s in names]
    comp = [100 * len(b[s]) / len(a[s]) for s in names]
    cols = [MIN if s in MINIMAL else MCP for s in names]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.5), dpi=200)
    bars = a1.barh(range(len(names)), med, color=cols, height=.62, lw=0)
    for i, v in enumerate(med):
        a1.text(v * 1.06, i, f"{v:,.0f}", va="center", fontsize=8.5, color=INK)
    a1.set_xscale("log"); a1.set_yticks(range(len(names)))
    a1.set_yticklabels([DISP[n] for n in names], color=INK); a1.invert_yaxis()
    a1.set_xlim(right=max(med) * 3)
    _style(a1, "Median input tokens per completed run  (log scale)", xlabel="input tokens")
    a1.grid(axis="y", visible=False); a1.grid(axis="x", color=GRID, lw=.7)
    a2.barh(range(len(names)), comp, color=cols, height=.62, lw=0)
    for i, (s, v) in enumerate(zip(names, comp)):
        a2.text(v + 2, i, f"{len(b[s])}/{len(a[s])}", va="center", fontsize=8.5, color=INK)
    a2.set_yticks(range(len(names)))
    a2.set_yticklabels([DISP[n] for n in names], color=INK)
    a2.invert_yaxis(); a2.set_xlim(0, 118)
    _style(a2, "Runs completing the whole task  (main matrix)", xlabel="% of runs")
    a2.grid(axis="y", visible=False); a2.grid(axis="x", color=GRID, lw=.7)
    h = [plt.Rectangle((0, 0), 1, 1, color=MIN), plt.Rectangle((0, 0), 1, 1, color=MCP)]
    lg = fig.legend(h, ["no MCP client", "can use MCP"], frameon=False, ncol=2,
                    loc="lower center", bbox_to_anchor=(.5, -.06), fontsize=8.5)
    for t in lg.get_texts(): t.set_color(MUTED)
    fig.tight_layout(); save(fig, "v8-scaffolding")


def fig_arms(done):
    by = defaultdict(dict)
    for r in done: by[r["scaffolding"]].setdefault(r["arm"], []).append(r)
    rows = []
    for s in ("hermes", "codex", "qwen-code", "claude-code"):
        d = by.get(s, {})
        c = st.median(x["total_input_tokens"] for x in d["cli"]) if d.get("cli") else None
        m = st.median(x["total_input_tokens"] for x in d["mcp"]) if d.get("mcp") else None
        rows.append((s, c, m, len(d.get("cli", [])), len(d.get("mcp", []))))
    fig, ax = plt.subplots(figsize=(7.8, 3.5), dpi=200)
    h = .34
    top = max(v for _, c, m, *_ in rows for v in (c or 0, m or 0))
    for i, (s, c, m, nc, nm) in enumerate(rows):
        if c: 
            ax.barh(i + h/2, c, height=h, color=CLI, lw=0)
            ax.text(c * 1.05, i + h/2, f"{c:,.0f}   {nc} run" + ("s" if nc != 1 else ""), va="center", fontsize=8, color=INK)
        if m:
            ax.barh(i - h/2, m, height=h, color=MCP, lw=0)
            ax.text(m * 1.05, i - h/2, f"{m:,.0f}   {nm} run" + ("s" if nm != 1 else ""), va="center", fontsize=8, color=INK)
        if c and m:
            ax.text(top * 3.6, i, f"×{m/c:.2f}", va="center", ha="right",
                    fontsize=9.5, color=INK, fontweight="bold")
        else:
            ax.text(top * 3.6, i, "undefined", va="center", ha="right",
                    fontsize=8.5, color=MUTED)
            ax.text(c * 1.05 if c else 1, i - h/2, "no completed MCP run",
                    va="center", fontsize=7.5, color=MUTED)
    ax.text(top * 3.6, -0.8, "MCP ÷ command line", va="center", ha="right",
            fontsize=8, color=MUTED)
    ax.set_xscale("log"); ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([DISP[r[0]] for r in rows], color=INK)
    ax.invert_yaxis(); ax.set_xlim(right=top * 4.2)
    _style(ax, "Median input tokens of completed runs, by arm",
           xlabel="input tokens (log scale)")
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color=GRID, lw=.7)
    h1 = [plt.Rectangle((0, 0), 1, 1, color=CLI), plt.Rectangle((0, 0), 1, 1, color=MCP)]
    lg = fig.legend(h1, ["command line", "MCP"], frameon=False, ncol=2,
                    loc="lower center", bbox_to_anchor=(.5, -.05), fontsize=8.5)
    for t in lg.get_texts(): t.set_color(MUTED)
    fig.tight_layout(); save(fig, "v8-arms")


def fig_catalogue(done):
    groups = {"MCP, fetched on demand\n(7 schemas per request)": [],
              "MCP, sent in full\n(44 schemas per request)": []}
    for r in done:
        if r["arm"] != "mcp": continue
        key = list(groups)[0] if r["scaffolding"] == "hermes" else list(groups)[1]
        groups[key].append((r["scaffolding"], r["total_input_tokens"]))
    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=200)
    tick = {}
    for i, k in enumerate(groups):
        vals = [v for _, v in groups[k]]
        m = st.median(vals)
        colour = MIN if i == 0 else MCP
        ax.bar(i, m, width=.5, color=colour, lw=0, zorder=2)
        ax.text(i, m * 1.08, f"median {m:,.0f}", ha="center", fontsize=9,
                color=INK, fontweight="bold")
        for _, v in groups[k]:
            ax.scatter(i + .34, v, s=40, color="white", edgecolor=colour, lw=1.6, zorder=4)
        names = sorted({DISP[n] for n, _ in groups[k]})
        tick[k] = f"\n{', '.join(names)}  ({len(vals)} completed runs)"
    ax.set_yscale("log")
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([k + tick[k] for k in groups], color=INK, fontsize=8.5)
    ax.set_xlim(-.55, len(groups) - .1)
    _style(ax, "Same MCP server, two delivery methods — completed MCP-arm runs",
           ylabel="input tokens (log scale)")
    ax.grid(axis="y", color=GRID, lw=.7)
    fig.tight_layout(); save(fig, "v8-catalogue")


if __name__ == "__main__":
    live, done = load()
    fig_scaffolding(live, done); fig_arms(done); fig_catalogue(done)
