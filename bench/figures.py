#!/usr/bin/env python3
"""Three figures, each answering one question.

The previous set had four charts that between them showed every column of the
dataset and answered nothing. These are built the other way round: each figure
exists because a specific claim in the paper needs evidence, and anything that
does not serve that claim is left out.

Palette: two categorical hues held in fixed order — CLI blue, MCP orange —
validated for colour-vision deficiency (worst adjacent pair ΔE 24.7 protan).
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from bench.insight import classify, load, orchestration_calls, paired  # noqa: E402

FIG = Path.home() / ("Documents/ludo-claude/ludo-writting-workshop/writting-projects"
                     "/papers/2026/mcp-vs-cli-benchmark/figures")

CLI, MCP = "#2a78d6", "#eb6834"
OTHER, DEAD = "#eda100", "#9a9891"
INK, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e2e1dd"


def _style(ax, title, ylabel=""):
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, fontsize=11, loc="left", pad=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")


def fig_purity(rows):
    """What each arm ACTUALLY did — the validity figure the paper turns on."""
    order = ["pure-cli", "pure-mcp", "web-api", "mixed", "no-tools"]
    colour = {"pure-cli": CLI, "pure-mcp": MCP, "web-api": OTHER,
              "mixed": "#8a6fb0", "no-tools": DEAD}
    counts = {a: defaultdict(int) for a in ("cli", "mcp")}
    for r in rows:
        if r.get("void"):
            continue
        counts[r["arm"]][classify(r)] += 1

    fig, ax = plt.subplots(figsize=(6.4, 2.5), dpi=200)
    for i, arm in enumerate(("cli", "mcp")):
        left = 0
        for k in order:
            v = counts[arm].get(k, 0)
            if not v:
                continue
            ax.barh(i, v, left=left, color=colour[k], height=0.55, linewidth=0)
            ax.text(left + v / 2, i, str(v), ha="center", va="center",
                    color="white", fontsize=8, fontweight="bold")
            left += v
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["assigned CLI", "assigned MCP"], color=MUTED, fontsize=9)
    ax.set_xlabel("runs", color=MUTED, fontsize=9)
    _style(ax, "What each run actually used, versus what it was assigned")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colour[k]) for k in order]
    leg = ax.legend(handles, ["shell only", "MCP only", "web API", "both",
                              "no tools"],
                    frameon=False, fontsize=8, ncol=5, loc="upper center",
                    bbox_to_anchor=(0.5, -0.28))
    for t in leg.get_texts():
        t.set_color(MUTED)
    fig.tight_layout()
    save(fig, "purity")


def fig_pairs(rows):
    """Paired token cost, contaminated pairs versus method-pure pairs."""
    loose = paired(rows, strict=False)
    strict = {(s, m) for s, m, _, _ in paired(rows, strict=True)}
    data = sorted(((k["total_input_tokens"] / c["total_input_tokens"], s, m)
                   for s, m, c, k in loose), key=lambda x: x[0])

    fig, ax = plt.subplots(figsize=(6.8, 4.2), dpi=200)
    ys = range(len(data))
    for y, (ratio, s, m) in zip(ys, data):
        pure = (s, m) in strict
        ax.barh(y, ratio, color=MCP if pure else GRID,
                edgecolor=MCP if pure else "#c9c7c1", height=0.62, linewidth=0.8)
        ax.text(ratio + 0.12, y, f"{ratio:.2f}×", va="center", fontsize=7.5,
                color=INK if pure else MUTED,
                fontweight="bold" if pure else "normal")
    ax.axvline(1.0, color=INK, linewidth=1, zorder=5)
    ax.text(1.05, len(data) - 0.4, "parity", fontsize=7.5, color=MUTED)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([f"{s}/{m}" for _, s, m in data], fontsize=7.5, color=MUTED)
    ax.set_xlabel("MCP tokens ÷ CLI tokens", color=MUTED, fontsize=9)
    _style(ax, "Token cost, MCP against CLI, same scaffolding and model")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=MCP),
               plt.Rectangle((0, 0), 1, 1, color=GRID)]
    leg = ax.legend(handles, ["both runs method-pure", "one or both contaminated"],
                    frameon=False, fontsize=8, loc="lower right")
    for t in leg.get_texts():
        t.set_color(MUTED)
    fig.tight_layout()
    save(fig, "pairs")


def fig_scaffolding(rows):
    """Cost and reliability by scaffolding, annotated with orchestration use."""
    agg = defaultdict(list)
    for r in rows:
        if r.get("void") or not r.get("total_input_tokens"):
            continue
        agg[r["scaffolding"]].append(r)
    items = sorted(agg.items(),
                   key=lambda kv: statistics.median(
                       x["total_input_tokens"] for x in kv[1]))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.6, 2.9), dpi=200,
                                 gridspec_kw={"width_ratios": [1.35, 1]})
    names = [k for k, _ in items]
    toks = [statistics.median(x["total_input_tokens"] for x in v) for _, v in items]
    orch = [sum(orchestration_calls(x) for x in v) for _, v in items]
    done = [100 * sum(1 for x in v if (x.get("completion_pct") or 0) == 100) / len(v)
            for _, v in items]

    bars = a1.bar(names, toks, color=[CLI if o == 0 else "#8a6fb0" for o in orch],
                  width=0.6, linewidth=0)
    for b, t in zip(bars, toks):
        a1.text(b.get_x() + b.get_width() / 2, t, f"{t:,.0f}", ha="center",
                va="bottom", fontsize=7.5, color=MUTED)
    a1.set_yscale("log")
    _style(a1, "Median tokens per run", "tokens (log)")

    b2 = a2.bar(names, done, color=[CLI if o == 0 else "#8a6fb0" for o in orch],
                width=0.6, linewidth=0)
    for b, d in zip(b2, done):
        a2.text(b.get_x() + b.get_width() / 2, d, f"{d:.0f}%", ha="center",
                va="bottom", fontsize=7.5, color=MUTED)
    a2.set_ylim(0, 118)
    _style(a2, "Runs completing the task in full", "% of runs")

    handles = [plt.Rectangle((0, 0), 1, 1, color=CLI),
               plt.Rectangle((0, 0), 1, 1, color="#8a6fb0")]
    leg = fig.legend(handles, ["no orchestration", "uses sub-agents / tool search"],
                     frameon=False, fontsize=8, ncol=2, loc="lower center",
                     bbox_to_anchor=(0.5, -0.06))
    for t in leg.get_texts():
        t.set_color(MUTED)
    fig.tight_layout()
    save(fig, "scaffolding")


def main():
    rows = load()
    fig_purity(rows)
    fig_pairs(rows)
    fig_scaffolding(rows)


if __name__ == "__main__":
    main()
