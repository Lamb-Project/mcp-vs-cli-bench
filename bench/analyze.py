#!/usr/bin/env python3
"""Build the results table and the paper's figures from results/runs.jsonl.

Figure conventions follow one rule that matters more than the rest: the two arms
are an *identity* distinction, so they get two categorical hues held in fixed
order across every figure — CLI is always blue, MCP always orange, whatever the
sort order or which cells survive. Colour never follows rank.

Palette validated for colour-vision deficiency (worst adjacent pair ΔE 24.7
protan, 33.6 normal) against the light chart surface.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "paper" / "figures"

# categorical slots 1 and 2, fixed to arms for the life of the paper
CLI_COLOR = "#2a78d6"
MCP_COLOR = "#eb6834"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
SURFACE = "#fcfcfb"
GRID = "#e2e1dd"

ARM_COLOR = {"cli": CLI_COLOR, "mcp": MCP_COLOR}
ARM_LABEL = {"cli": "CLI", "mcp": "MCP"}


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def cell_key(r: dict) -> tuple[str, str]:
    return (r["scaffolding"], r["model"])


def markdown_table(rows: list[dict]) -> str:
    """The results table. Void cells are shown with their reason, never as zeros."""
    hdr = ("| Scaffolding | Model | Arm | Init tok | Total in | Cache % | Tools | "
           "Tool ok | Done % | Cost $ | Wall s |")
    sep = "|" + "---|" * 11
    out = [hdr, sep]
    for r in sorted(rows, key=lambda r: (r["scaffolding"], r["model"], r["arm"])):
        if r.get("void"):
            out.append(f"| {r['scaffolding']} | {r['model']} | {ARM_LABEL[r['arm']]} | "
                       f"⛔ | | | | | | | | <!-- {r.get('void_reason')} -->")
            continue
        f = lambda v, s="": "—" if v is None else f"{v:{s}}"  # noqa: E731
        out.append(
            f"| {r['scaffolding']} | {r['model']} | {ARM_LABEL[r['arm']]} "
            f"| {f(r.get('initial_tokens'), ',')} | {f(r.get('total_input_tokens'), ',')} "
            f"| {f(r.get('cache_hit_pct'))} | {r.get('tool_calls', 0)} "
            f"| {f(r.get('tool_success_ratio'))} | {f(r.get('completion_pct'))} "
            f"| {f(r.get('theoretical_cost_usd'), '.4f')} | {f(r.get('wall_s'))} |")
    return "\n".join(out)


def _style(ax, ylabel: str, title: str) -> None:
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    ax.set_ylabel(ylabel, color=INK_MUTED, fontsize=9)
    ax.set_title(title, color=INK, fontsize=11, loc="left", pad=12)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_MUTED, labelsize=8, length=0)


def grouped_bars(rows, field, ylabel, title, outfile, logy=False):
    """One grouped bar chart: cells on x, two arms side by side."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_cell: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for r in rows:
        if r.get("void") or r.get(field) is None:
            continue
        by_cell[cell_key(r)][r["arm"]] = r[field]
    cells = [c for c in sorted(by_cell) if by_cell[c]]
    if not cells:
        return None

    fig, ax = plt.subplots(figsize=(max(6.5, 0.85 * len(cells)), 3.6), dpi=200)
    width = 0.38
    xs = range(len(cells))
    for i, arm in enumerate(("cli", "mcp")):
        vals = [by_cell[c].get(arm) for c in cells]
        offs = [x + (i - 0.5) * (width + 0.02) for x in xs]
        pts = [(o, v) for o, v in zip(offs, vals) if v is not None]
        if not pts:
            continue
        ax.bar([p[0] for p in pts], [p[1] for p in pts], width=width,
               color=ARM_COLOR[arm], label=ARM_LABEL[arm], zorder=3,
               linewidth=0)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{s}\n{m}" for s, m in cells], fontsize=7,
                       color=INK_MUTED)
    if logy:
        ax.set_yscale("log")
    _style(ax, ylabel, title)
    leg = ax.legend(frameon=False, fontsize=8, loc="upper left",
                    bbox_to_anchor=(0, 1.02), ncol=2)
    for txt in leg.get_texts():
        txt.set_color(INK_MUTED)
    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"{outfile}.{ext}", facecolor=SURFACE,
                    bbox_inches="tight")
    plt.close(fig)
    return FIGDIR / f"{outfile}.pdf"


def tool_register_summary(rows: list[dict]) -> str:
    """Which tools were actually called — the register, aggregated per arm."""
    agg: dict[str, dict[str, int]] = {"cli": defaultdict(int), "mcp": defaultdict(int)}
    for r in rows:
        if r.get("void"):
            continue
        for name, n in (r.get("tool_register") or {}).items():
            agg[r["arm"]][name] += n
    out = ["| Arm | Tool | Calls |", "|---|---|---|"]
    for arm in ("cli", "mcp"):
        for name, n in sorted(agg[arm].items(), key=lambda kv: -kv[1])[:12]:
            out.append(f"| {ARM_LABEL[arm]} | `{name}` | {n} |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(ROOT / "results" / "runs.jsonl"))
    args = ap.parse_args()
    rows = load(Path(args.runs))
    live = [r for r in rows if not r.get("void")]
    print(f"{len(rows)} cells, {len(live)} live, {len(rows)-len(live)} void\n")
    print(markdown_table(rows))
    print("\n### Tool register\n")
    print(tool_register_summary(rows))

    figs = [
        grouped_bars(rows, "total_input_tokens", "total input tokens",
                     "Total input tokens per run, by surface", "tokens", logy=True),
        grouped_bars(rows, "tool_calls", "tool calls",
                     "Tool calls to complete the same workflow", "toolcalls"),
        grouped_bars(rows, "completion_pct", "task completion (%)",
                     "Task completion against the five-item rubric", "completion"),
        grouped_bars(rows, "theoretical_cost_usd", "USD (list price)",
                     "Theoretical cost per run at OpenRouter list prices", "cost"),
    ]
    print("\nfigures:", ", ".join(str(f.name) for f in figs if f))


if __name__ == "__main__":
    main()
