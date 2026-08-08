#!/usr/bin/env python3
"""Draft 6 tables, computed on runs that completed the task.

The governing rule: cost answers "what did doing this job cost", and that
question has no answer where the job was not done. An agent that abandons a task
early is cheap, so pooling failed runs with successful ones flatters whichever
arm fails more — which in this study is the MCP arm. Cost is therefore reported
over complete runs only, completion is reported separately as its own quantity,
and pooled figures appear only as a robustness check.
"""
from __future__ import annotations
import json, os, pathlib, statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Draft 8 reports e3-final; draft 9 adds the Claude Code row in e4-final. Both
# stay reproducible from one script rather than two, because a forked analysis
# is how a figure and a table start disagreeing about the same quantity.
DATASET = os.environ.get("BENCH_DATASET", "e3-final.jsonl")
MINIMAL = {"pi", "tau"}
DISP = {"pi": "pi", "tau": "Tau", "hermes": "Hermes", "codex": "Codex",
        "qwen-code": "qwen-code", "claude-code": "Claude Code",
        "opencode": "opencode"}


def load():
    rs = [json.loads(l) for l in (ROOT / "results" / DATASET).read_text().splitlines() if l.strip()]
    live = [r for r in rs if not r.get("void") and r.get("total_input_tokens")]
    done = [r for r in live if (r.get("completion_pct") or 0) == 100]
    return rs, live, done


def med(rs, key="total_input_tokens"):
    return st.median(r[key] for r in rs)


def table1(live, done):
    """Cost of a completed run, by scaffolding, with completion beside it."""
    a, b = defaultdict(list), defaultdict(list)
    for r in live: a[r["scaffolding"]].append(r)
    for r in done: b[r["scaffolding"]].append(r)
    order = sorted(b, key=lambda s: med(b[s]))
    base = med(b[order[0]])
    lines = ["| Scaffolding | MCP | Completed | Input | Output | Relative | Cost |",
             "|---|:--:|---:|---:|---:|---:|---:|"]
    for s in order:
        lines.append(
            f"| {DISP[s]} | {'no' if s in MINIMAL else 'yes'} | "
            f"{len(b[s])}/{len(a[s])} | {med(b[s]):,.0f} | "
            f"{med(b[s], 'total_output_tokens'):,.0f} | ×{med(b[s])/base:.1f} | "
            f"${med(b[s], 'theoretical_cost_usd'):.4f} |")
    return "\n".join(lines), order, base


def table2(done):
    """Command-line arm only: no MCP catalogue attached to anything."""
    d = defaultdict(list)
    for r in done:
        if r["arm"] == "cli": d[r["scaffolding"]].append(r)
    order = sorted(d, key=lambda s: med(d[s]))
    base = med(d["pi"])
    lines = ["| Scaffolding | MCP client | Runs | Tokens | vs pi | Cache | Cost |",
             "|---|:--:|---:|---:|---:|---:|---:|"]
    for s in order:
        ch = [r["cache_hit_pct"] for r in d[s] if r.get("cache_hit_pct") is not None]
        lines.append(
            f"| {DISP[s]} | {'**no**' if s in MINIMAL else 'yes'} | {len(d[s])} | "
            f"{med(d[s]):,.0f} | ×{med(d[s])/base:.1f} | "
            f"{f'{st.median(ch):.0f}%' if ch else '—'} | "
            f"${med(d[s], 'theoretical_cost_usd'):.4f} |")
    return "\n".join(lines)


def table3(done):
    """The two arms within each MCP-capable scaffolding, completed runs only."""
    by = defaultdict(dict)
    for r in done: by[r["scaffolding"]].setdefault(r["arm"], []).append(r)
    lines = ["| Scaffolding | Command line | MCP | Ratio | Runs (cmd / MCP) |",
             "|---|---:|---:|---:|:--:|"]
    for s in ("hermes", "codex", "opencode", "qwen-code", "claude-code"):
        d = by.get(s, {})
        if "cli" in d and "mcp" in d:
            c, m = med(d["cli"]), med(d["mcp"])
            lines.append(f"| {DISP[s]} | {c:,.0f} | {m:,.0f} | ×{m/c:.2f} | "
                         f"{len(d['cli'])} / {len(d['mcp'])} |")
        else:
            have = ", ".join(f"{len(v)} in the {k} arm" for k, v in d.items())
            lines.append(f"| {DISP[s]} | — | — | undefined | {have or 'none'} |")
    return "\n".join(lines)


def table_models(done, live):
    """Per-model results: the dimension draft 5 dropped."""
    a, b = defaultdict(list), defaultdict(list)
    for r in live: a[r["model"]].append(r)
    for r in done: b[r["model"]].append(r)
    lines = ["| Model | Served | Completed | Tokens | Cost | Cost, cached discounted |",
             "|---|---|---:|---:|---:|---:|"]
    SERVED = {"gpt-5.6-luna": "OpenAI", "gpt-5.6-terra": "OpenAI",
              "sonnet-5": "Anthropic", "glm-5.2": "local", "qwen3.6:27b": "local"}
    for m in sorted(b, key=lambda m: med(b[m], "theoretical_cost_usd")):
        lines.append(
            f"| `{m}` | {SERVED[m]} | {len(b[m])}/{len(a[m])} | {med(b[m]):,.0f} | "
            f"${med(b[m], 'theoretical_cost_usd'):.4f} | "
            f"${med(b[m], 'cost_usd_cached_discounted'):.4f} |")
    return "\n".join(lines)


def sensitivity(done):
    """Does the MCP penalty survive a cached-read discount?"""
    out = ["| Arm | Runs | Tokens | Cost, list price | Cost, cached discounted |",
           "|---|---:|---:|---:|---:|"]
    for arm, lbl in (("cli", "Command line"), ("mcp", "MCP")):
        sub = [r for r in done if r["arm"] == arm and r["scaffolding"] not in MINIMAL]
        out.append(f"| {lbl} | {len(sub)} | {med(sub):,.0f} | "
                   f"${med(sub, 'theoretical_cost_usd'):.4f} | "
                   f"${med(sub, 'cost_usd_cached_discounted'):.4f} |")
    return "\n".join(out)


def waste(live):
    """Tokens and money spent on runs that delivered nothing.

    A run that fails returns no completed work for its tokens, so its cost per
    unit of delivered work is unbounded. That is not a reliability footnote; it
    is a cost, and it belongs in the cost analysis. Reported over every live run,
    so nothing is excluded and no imputation is required.
    """
    out = ["| Group | Runs | Failed | Wasted tokens | Wasted % | Wasted cost % |",
           "|---|---:|---:|---:|---:|---:|"]
    groups = [("Command-line arm",
               lambda r: r["arm"] == "cli" and r["scaffolding"] not in MINIMAL),
              ("MCP arm", lambda r: r["arm"] == "mcp" and r["scaffolding"] not in MINIMAL),
              ("No MCP client", lambda r: r["scaffolding"] in MINIMAL)]
    for lbl, sel in groups:
        sub = [r for r in live if sel(r)]
        bad = [r for r in sub if (r.get("completion_pct") or 0) < 100]
        tt = sum(r["total_input_tokens"] for r in sub)
        ft = sum(r["total_input_tokens"] for r in bad)
        tc = sum(r.get("theoretical_cost_usd") or 0 for r in sub)
        fc = sum(r.get("theoretical_cost_usd") or 0 for r in bad)
        out.append(f"| {lbl} | {len(sub)} | {len(bad)} | {ft:,} | "
                   f"{100*ft/tt:.1f}% | {100*fc/tc:.1f}% |")
    return "\n".join(out)


if __name__ == "__main__":
    rs, live, done = load()
    print(f"# {len(rs)} cells · {len(live)} live · {len(done)} completed\n")
    t1, order, base = table1(live, done)
    print("## Table 1 — by scaffolding, completed runs\n"); print(t1)
    print(f"\nspan: ×{med([r for r in done if r['scaffolding']==order[-1]])/base:.0f}\n")
    print("## Table 2 — command-line arm only\n"); print(table2(done))
    print("\n## Table 3 — arms within scaffolding\n"); print(table3(done))
    print("\n## Table 4 — by model\n"); print(table_models(done, live))
    print("\n## Table 5 — cost sensitivity\n"); print(sensitivity(done))
    print("\n## Table 6 — cost of failure\n"); print(waste(live))
