#!/usr/bin/env python3
"""Figures and tables for draft v3 — Experiments 1 and 3 side by side.

Each figure answers one question. Experiment 2 produces no figure: it completed
nothing, and a chart of flailing would imply the numbers mean something.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from bench.insight import classify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIG = Path.home() / ("Documents/ludo-claude/ludo-writting-workshop/writting-projects"
                     "/papers/2026/mcp-vs-cli-benchmark/figures")
CLI, MCP, OTHER, MIX, DEAD = "#2a78d6", "#eb6834", "#eda100", "#8a6fb0", "#9a9891"
INK, MUTED, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e2e1dd"


def load(n):
    p = ROOT / "results" / n
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _style(ax, title, ylabel=""):
    ax.set_facecolor(SURF); ax.figure.set_facecolor(SURF)
    ax.set_title(title, color=INK, fontsize=10.5, loc="left", pad=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{e}", facecolor=SURF, bbox_inches="tight")
    plt.close(fig); print(f"  {name}")


def fig_isolation(e1, e3):
    """Did the isolation work? Experiment 1 against Experiment 3."""
    order = ["pure-cli", "pure-mcp", "web-api", "mixed", "no-tools"]
    col = {"pure-cli": CLI, "pure-mcp": MCP, "web-api": OTHER,
           "mixed": MIX, "no-tools": DEAD}
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 2.6), dpi=200, sharex=True)
    for ax, rows, lab in ((axes[0], e1, "Experiment 1 — public fixture"),
                          (axes[1], e3, "Experiment 3 — private, isolated")):
        c = {a: defaultdict(int) for a in ("cli", "mcp")}
        for r in rows:
            if not r.get("void"):
                c[r["arm"]][classify(r)] += 1
        for i, arm in enumerate(("cli", "mcp")):
            left = 0
            for k in order:
                v = c[arm].get(k, 0)
                if not v:
                    continue
                ax.barh(i, v, left=left, color=col[k], height=0.55, lw=0)
                ax.text(left + v / 2, i, str(v), ha="center", va="center",
                        color="white", fontsize=8, fontweight="bold")
                left += v
        ax.set_yticks([0, 1]); ax.set_yticklabels(["CLI arm", "MCP arm"],
                                                  color=MUTED, fontsize=9)
        _style(ax, lab); ax.grid(axis="y", visible=False)
        ax.set_xlabel("runs", color=MUTED, fontsize=9)
    h = [plt.Rectangle((0, 0), 1, 1, color=col[k]) for k in order]
    lg = fig.legend(h, ["shell only", "MCP only", "web API", "both", "no tools"],
                    frameon=False, fontsize=8, ncol=5, loc="lower center",
                    bbox_to_anchor=(0.5, -0.13))
    for t in lg.get_texts():
        t.set_color(MUTED)
    fig.tight_layout(); save(fig, "isolation")


def fig_ratios(e3):
    """Experiment 3 ratios, with the reporting gate made visible."""
    by = defaultdict(dict)
    for r in e3:
        if not r.get("void"):
            by[(r["scaffolding"], r["model"])][r["arm"]] = r
    data = []
    for (s, m), a in by.items():
        c, k = a.get("cli"), a.get("mcp")
        if not (c and k and c.get("total_input_tokens") and k.get("total_input_tokens")):
            continue
        ratio = k["total_input_tokens"] / c["total_input_tokens"]
        ok = (classify(c) == "pure-cli" and classify(k) == "pure-mcp"
              and (c.get("completion_pct") or 0) == 100
              and (k.get("completion_pct") or 0) == 100)
        incomplete = ((c.get("completion_pct") or 0) < 100
                      or (k.get("completion_pct") or 0) < 100)
        data.append((ratio, f"{s}/{m}", ok, incomplete))
    data.sort()
    fig, ax = plt.subplots(figsize=(6.8, 3.4), dpi=200)
    for y, (ratio, name, ok, inc) in enumerate(data):
        colour = MCP if ok else (DEAD if inc else GRID)
        ax.barh(y, ratio, color=colour, height=0.6, lw=0.8,
                edgecolor=MCP if ok else "#c9c7c1")
        ax.text(ratio * 1.05, y, f"{ratio:.2f}×", va="center", fontsize=7.5,
                color=INK if ok else MUTED)
    ax.axvline(1.0, color=INK, lw=1, zorder=5)
    ax.set_xscale("log")
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels([d[1] for d in data], fontsize=7.5, color=MUTED)
    ax.set_xlabel("MCP tokens ÷ CLI tokens (log)", color=MUTED, fontsize=9)
    _style(ax, "Experiment 3 — token ratio, with the reporting gate applied")
    ax.grid(axis="y", visible=False); ax.grid(axis="x", color=GRID, lw=0.8)
    h = [plt.Rectangle((0, 0), 1, 1, color=MCP),
         plt.Rectangle((0, 0), 1, 1, color=DEAD)]
    lg = ax.legend(h, ["reportable (both complete, both pure)",
                       "an arm did not complete — ratio not meaningful"],
                   frameon=False, fontsize=7.5, loc="lower right")
    for t in lg.get_texts():
        t.set_color(MUTED)
    fig.tight_layout(); save(fig, "ratios")


def fig_scaffolding(e1):
    """Cost against reliability by scaffolding, Experiment 1."""
    agg = defaultdict(list)
    for r in e1:
        if not r.get("void") and r.get("total_input_tokens"):
            agg[r["scaffolding"]].append(r)
    items = sorted(agg.items(),
                   key=lambda kv: st.median(x["total_input_tokens"] for x in kv[1]))
    names = [k for k, _ in items]
    toks = [st.median(x["total_input_tokens"] for x in v) for _, v in items]
    done = [100 * sum(1 for x in v if (x.get("completion_pct") or 0) == 100) / len(v)
            for _, v in items]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.8), dpi=200)
    for ax, vals, title, ylab, logy in (
            (a1, toks, "Median tokens per run", "tokens (log)", True),
            (a2, done, "Runs completing in full", "% of runs", False)):
        b = ax.bar(names, vals, color=[CLI if n == "pi" else MIX for n in names],
                   width=0.6, lw=0)
        for bb, v in zip(b, vals):
            ax.text(bb.get_x() + bb.get_width() / 2, v,
                    f"{v:,.0f}" if logy else f"{v:.0f}%", ha="center",
                    va="bottom", fontsize=7.5, color=MUTED)
        if logy:
            ax.set_yscale("log")
        else:
            ax.set_ylim(0, 118)
        _style(ax, title, ylab)
    fig.tight_layout(); save(fig, "scaffolding")


def table(rows, title):
    out = [f"**{title}**", "",
           "| Scaffolding | Model | Arm | Total tokens | Uncached | Calls | Pure? | Completion |",
           "|---|---|---|---:|---:|---:|:--:|---:|"]
    for r in sorted(rows, key=lambda r: (r["scaffolding"], r["model"], r["arm"])):
        if r.get("void"):
            out.append(f"| {r['scaffolding']} | {r['model']} | {r['arm'].upper()} "
                       f"| ⛔ | | | | *{r.get('void_reason','')[:34]}* |")
            continue
        ti = r.get("total_input_tokens")
        pre = (ti - (r.get("cached_tokens") or 0)) if ti else None
        cl = classify(r)
        pure = "✔" if ((r["arm"] == "cli" and cl == "pure-cli")
                       or (r["arm"] == "mcp" and cl == "pure-mcp")) else f"✗ {cl}"
        f = lambda v: "—" if v is None else f"{v:,}"  # noqa: E731
        out.append(f"| {r['scaffolding']} | {r['model']} | {r['arm'].upper()} "
                   f"| {f(ti)} | {f(pre)} | {r.get('tool_calls','—')} | {pure} "
                   f"| {r.get('completion_pct','—')}% |")
    return "\n".join(out)


def main():
    e1, e3 = load("runs-rerun.jsonl"), load("runs-e3.jsonl")
    fig_isolation(e1, e3); fig_ratios(e3); fig_scaffolding(e1)
    (ROOT / "results" / "tables-v3.md").write_text(
        table(e1, "Table 1 — Experiment 1 (re-run, uniform routing, public fixture)")
        + "\n\n" +
        table(e3, "Table 2 — Experiment 3 (private fixture, isolated arms)") + "\n")
    print("  tables-v3.md")


if __name__ == "__main__":
    main()
