#!/usr/bin/env python3
"""Recompute Section 8.1 over every repetition, including the Claude Code row.

Draft 8's replication covered five scaffoldings on local models. Claude Code was
absent because the harness believed it could not reach a local endpoint, so the
one scaffolding with no independent measurement also had no repetitions. It has
three passes now, and every number in Section 8.1 moves: the executed/completed
counts, the per-configuration spread, and the completion-by-condition table.

Run-to-run spread is largest ÷ smallest total input tokens across the completed
repetitions of one configuration, as in draft 8.
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
MINIMAL = {"pi", "tau"}
REP_FILES = ["runs-local-rep1.jsonl", "runs-local-rep2.jsonl",
             "runs-local-rep3.jsonl",
             "runs-cc-rep1.jsonl", "runs-cc-rep2.jsonl", "runs-cc-rep3.jsonl",
             "runs-opencode-rep1.jsonl", "runs-opencode-rep2.jsonl",
             "runs-opencode-rep3.jsonl"]


def load(name):
    p = R / name
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def norm(r):
    """Draft 8's four-item completion rule (pr_links_issue is unsatisfiable)."""
    rub = r.get("rubric") or {}
    valid = {k: v for k, v in rub.items() if k != "pr_links_issue"}
    if valid:
        r["completion_pct"] = round(
            100.0 * sum(bool(v) for v in valid.values()) / len(valid), 1)
    return r


def main():
    rows = []
    for f in REP_FILES:
        got = [norm(r) for r in load(f)]
        if got:
            print(f"  {f:<26} {len(got):>3} runs")
        rows.append((f, got))
    allrows = [r for _, got in rows for r in got]
    # Same filter the rest of the analysis uses: a run with no token count was
    # not measured, so it is not an attempt the completion rates can speak about.
    # Without the token condition the denominators come out 18/18 against the
    # paper's 17/17 and 13/17.
    live = [r for r in allrows if not r.get("void") and r.get("total_input_tokens")]
    done = [r for r in live if (r.get("completion_pct") or 0) == 100]
    print(f"\n  {len(live)} executed, {len(done)} completed\n")

    # --- per-configuration spread over completed repetitions ---------------
    by_cfg = defaultdict(list)
    for r in done:
        if r.get("total_input_tokens"):
            by_cfg[(r["scaffolding"], r["model"], r["arm"])].append(
                r["total_input_tokens"])
    spreads = {k: max(v) / min(v) for k, v in by_cfg.items() if len(v) > 1}
    print("=" * 74)
    print("SPREAD, largest / smallest input tokens, completed repetitions only")
    print("=" * 74)
    for k in sorted(spreads, key=lambda k: -spreads[k]):
        n = len(by_cfg[k])
        mark = "  <- Claude Code" if k[0] == "claude-code" else ""
        print(f"  {k[0]:<12}{k[1]:<13}{k[2]:<4} n={n}  "
              f"x{spreads[k]:.2f}{mark}")
    if spreads:
        print(f"\n  configurations with >1 completed repetition: {len(spreads)}")
        print(f"  MEDIAN spread  x{st.median(spreads.values()):.2f}")
        print(f"  WIDEST spread  x{max(spreads.values()):.2f}")

    # --- completion by condition -------------------------------------------
    print("\n" + "=" * 74)
    print("COMPLETION BY CONDITION")
    print("=" * 74)
    for label, sel in (
            ("Command-line arm", lambda r: r["arm"] == "cli"
             and r["scaffolding"] not in MINIMAL),
            ("MCP arm", lambda r: r["arm"] == "mcp"
             and r["scaffolding"] not in MINIMAL),
            ("Scaffoldings with no MCP client", lambda r: r["scaffolding"] in MINIMAL)):
        sub = [r for r in live if sel(r)]
        ok = [r for r in sub if (r.get("completion_pct") or 0) == 100]
        print(f"  {label:<34} {len(ok)}/{len(sub)}")

    # --- the Claude Code row on its own ------------------------------------
    cc = [r for r in live if r["scaffolding"] == "claude-code"]
    if cc:
        print("\n" + "=" * 74)
        print("CLAUDE CODE ROW, every repetition")
        print("=" * 74)
        for r in sorted(cc, key=lambda r: (r["model"], r["arm"])):
            print(f"  {r['model']:<13}{r['arm']:<4} "
                  f"done={str(r.get('completion_pct')):<6} "
                  f"in={str(r.get('total_input_tokens')):>9} "
                  f"tools={r.get('tool_calls'):>3} "
                  f"mcp={r.get('mcp_tools_used'):>2} "
                  f"wall={r.get('wall_s')}")


if __name__ == "__main__":
    main()
