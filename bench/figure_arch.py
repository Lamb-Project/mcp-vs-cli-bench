#!/usr/bin/env python3
"""Architecture of the measurement harness.

The diagram carries an argument, not just boxes: every scaffolding under test is
reached the same way — as a subprocess with a command line — which is what makes
one script able to drive six of them. The telemetry sits on the model side, so a
scaffolding cannot under-report by delegating to a sub-agent.
"""
from __future__ import annotations
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = (pathlib.Path.home() / "Documents/ludo-claude/ludo-writting-workshop"
       "/writting-projects/papers/2026/mcp-vs-cli-benchmark/figures")

INK, MUTED, SURF = "#111111", "#575757", "#ffffff"
BLUE, ORANGE, GREEN, GREY = "#2a6fdb", "#e2622a", "#1f9d63", "#8a8a8a"
BAND = "#f2f2f0"


def box(ax, x, y, w, h, label, sub="", fc="white", ec=BLUE, lw=1.4, fs=9, bold=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, zorder=3))
    ax.text(x + w/2, y + h/2 + (0.018 if sub else 0), label, ha="center", va="center",
            fontsize=fs, color=INK, fontweight="bold" if bold else "normal", zorder=4)
    if sub:
        ax.text(x + w/2, y + h/2 - 0.030, sub, ha="center", va="center",
                fontsize=fs - 1.6, color=MUTED, zorder=4)


def arrow(ax, p, q, color=GREY, style="-|>", lw=1.3, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=11,
                                 color=color, lw=lw, linestyle=ls, zorder=2,
                                 connectionstyle=f"arc3,rad={rad}"))


def main():
    fig, ax = plt.subplots(figsize=(8.6, 6.2), dpi=200)
    ax.set_xlim(0, 1); ax.set_ylim(-0.075, 1); ax.axis("off")
    fig.patch.set_facecolor(SURF)

    # ---- band 1: design -------------------------------------------------
    ax.add_patch(plt.Rectangle((0.02, 0.845), 0.96, 0.150, fc=BAND, ec="none", zorder=0))
    ax.text(0.035, 0.978, "DESIGN  (once)", fontsize=7.5, color=MUTED,
            fontweight="bold", va="top")
    box(ax, 0.09, 0.858, 0.36, 0.072, "Claude Code",
        "task, prompts, fixture, verifier", ec=GREY, fc="white")
    box(ax, 0.55, 0.858, 0.36, 0.072, "AAWD methodology",
        "phases P1–P5", ec=GREY, fc="white", bold=False)
    arrow(ax, (0.55, 0.894), (0.45, 0.894), color=GREY, style="<|-")

    # ---- band 2: orchestration -----------------------------------------
    box(ax, 0.30, 0.735, 0.40, 0.070, "orchestration script  (bash)",
        "reset · select cell · invoke · verify", ec=INK, fc="white", lw=1.6)
    arrow(ax, (0.27, 0.858), (0.30, 0.805), color=GREY, rad=-0.2)

    # ---- band 3: the six scaffoldings ----------------------------------
    ax.add_patch(plt.Rectangle((0.02, 0.475), 0.96, 0.215, fc=BAND, ec="none", zorder=0))
    ax.text(0.035, 0.686, "SIX AGENT SCAFFOLDINGS  —  each invoked as a subprocess "
            "with a command line", fontsize=7.5, color=MUTED, fontweight="bold", va="top")
    names = [("pi", GREEN), ("Tau", GREEN), ("Hermes", ORANGE),
             ("Codex", ORANGE), ("qwen-code", ORANGE), ("Claude Code", ORANGE)]
    w, gap = 0.135, 0.019
    x0 = (1 - (len(names)*w + (len(names)-1)*gap)) / 2
    for i, (n, c) in enumerate(names):
        x = x0 + i*(w + gap)
        box(ax, x, 0.545, w, 0.078, n, "no MCP" if c == GREEN else "MCP arm\n+ CLI arm",
            ec=c, fc="white", fs=8.5)
        if n == "Claude Code":
            # Bypasses the proxy: authenticates to Anthropic on a subscription
            # account, so its usage figures are self-reported.
            ax.add_patch(FancyArrowPatch((x + w/2, 0.545), (0.8625, 0.267),
                                         arrowstyle="-|>", mutation_scale=11,
                                         color=c, lw=1.2, linestyle=(0, (3, 2)),
                                         zorder=2))
            ax.text(0.883, 0.40, "direct — bypasses the proxy;\nusage self-reported",
                    fontsize=6.8, color=c, va="center", ha="left")
        else:
            arrow(ax, (x + w/2, 0.545), (x + w/2, 0.435), color=c, lw=1.1)
    arrow(ax, (0.50, 0.735), (0.50, 0.625), color=INK, lw=1.5)

    # ---- band 4: broker -------------------------------------------------
    box(ax, 0.085, 0.345, 0.715, 0.088, "LiteLLM proxy",
        "one accounting path for five of the six · tokens, cache, tool calls, schemas",
        ec=BLUE, fc="white", lw=1.7)

    # ---- band 5: models -------------------------------------------------
    # The proxy fans out to the endpoints it actually brokers. Anthropic is not
    # among them: only Claude Code uses an Anthropic model, and it reaches the
    # vendor directly on its subscription, so that box hangs off Claude Code.
    for x, lbl, sub in ((0.115, "OpenAI", "hosted"), (0.475, "local GPU", "open-weight")):
        box(ax, x, 0.195, 0.215, 0.072, lbl, sub, ec=GREY, fc="white", fs=8.5, bold=False)
        arrow(ax, (x + 0.1075, 0.345), (x + 0.1075, 0.267), color=GREY, lw=1.1)
    box(ax, 0.755, 0.195, 0.215, 0.072, "Anthropic", "subscription",
        ec=ORANGE, fc="white", fs=8.5, bold=False)

    # ---- band 6: the world + verification -------------------------------
    box(ax, 0.06, 0.045, 0.38, 0.072, "private GitHub fixture",
        "reset before every run", ec=GREY, fc="white", fs=8.5, bold=False)
    box(ax, 0.56, 0.045, 0.38, 0.072, "verifier",
        "reads repo state via API", ec=GREEN, fc="white", fs=8.5)
    arrow(ax, (0.44, 0.081), (0.56, 0.081), color=GREEN)
    # agents act on the fixture
    # the acting path leaves the scaffolding band as a whole
    ax.add_patch(FancyArrowPatch((0.038, 0.545), (0.038, 0.121), arrowstyle="-|>",
                                 mutation_scale=11, color=MUTED, lw=1.1,
                                 linestyle=(0, (4, 3)), zorder=2))
    ax.text(0.055, 0.30, "agents act on the repository\n(gh · git · MCP tools)",
            fontsize=7.2, color=MUTED, va="center")
    # verifier result returns to the script
    arrow(ax, (0.94, 0.081), (0.94, 0.770), color=GREEN, ls=(0, (4, 3)), lw=1.1)
    arrow(ax, (0.94, 0.770), (0.70, 0.770), color=GREEN, ls=(0, (4, 3)), lw=1.1)
    ax.text(0.962, 0.60, "completion\n(4 checks)", fontsize=7.2, color=GREEN,
            va="center", rotation=90, ha="center")

    ax.text(0.50, -0.058,
            "Claude Code appears twice: it was used in the design and orchestration "
            "of the study, and is also one of the six scaffoldings measured by it.\n"
            "It is the one scaffolding that does not cross the proxy — it "
            "authenticates to Anthropic directly, so its usage is self-reported.",
            ha="center", fontsize=7.0, color=MUTED, style="italic")
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"v5-architecture.{ext}", facecolor=SURF, bbox_inches="tight")
    print("  v5-architecture")


if __name__ == "__main__":
    main()
