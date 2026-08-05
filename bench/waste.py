#!/usr/bin/env python3
"""How much of the work was not work?

Three categories, counted per run from the tool register:

  navel-gazing  calls that interrogate the agent's own situation rather than the
                task — who am I, what tools do I have, what resources exist.
  redundant     re-deriving something the prompt already supplied, most often
                searching for a repository whose full name was given.
  repetition    the same tool called far more times than the task requires,
                which is the signature of a loop rather than progress.

None of these advance the task. Together they are the cost of an agent being
confused about its own surface, and the question is whether attaching a tool
catalogue produces more of it.
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NAVEL = ("get_me", "list_mcp_resources", "list_mcp_resource_templates",
         "tool_search", "ToolSearch", "check_permissions", "list_tools")
REDUNDANT = ("search_repositories", "search_users")
# a task needing ~6 operations should not call one tool more than this
REPEAT_LIMIT = 6


def load(name):
    return [json.loads(l) for l in (ROOT / "results" / name).read_text().splitlines()
            if l.strip()]


def waste(r: dict) -> tuple[int, int, int, list[str]]:
    reg = r.get("tool_register") or {}
    navel = sum(n for k, n in reg.items() if any(w in k for w in NAVEL))
    redun = sum(n for k, n in reg.items() if any(w in k for w in REDUNDANT))
    repeat = sum(max(0, n - REPEAT_LIMIT) for k, n in reg.items())
    detail = [f"{k}×{n}" for k, n in sorted(reg.items(), key=lambda kv: -kv[1])
              if any(w in k for w in NAVEL + REDUNDANT) or n > REPEAT_LIMIT]
    return navel, redun, repeat, detail


def report(rows, label):
    print("=" * 76)
    print(f"{label}")
    print("=" * 76)

    per_arm = defaultdict(lambda: [0, 0, 0, 0, 0])   # calls, navel, redun, repeat, runs
    per_scaf = defaultdict(lambda: [0, 0, 0, 0, 0])
    worst = []
    for r in rows:
        if r.get("void") or not r.get("tool_calls"):
            continue
        n, d, rep, detail = waste(r)
        for agg, key in ((per_arm, r["arm"]), (per_scaf, r["scaffolding"])):
            a = agg[key]
            a[0] += r["tool_calls"]; a[1] += n; a[2] += d; a[3] += rep; a[4] += 1
        if n + d + rep:
            worst.append((n + d + rep, r, detail))

    print(f"\n  {'arm':<6}{'runs':>5}{'calls':>7}{'wasted':>8}{'% wasted':>10}")
    for arm in ("cli", "mcp"):
        c, n, d, rep, runs = per_arm[arm]
        w = n + d + rep
        if c:
            print(f"  {arm.upper():<6}{runs:>5}{c:>7}{w:>8}{100*w/c:>9.1f}%")

    print(f"\n  {'scaffolding':<13}{'runs':>5}{'calls':>7}{'navel':>7}{'redun':>7}"
          f"{'repeat':>8}{'% wasted':>10}")
    for s, (c, n, d, rep, runs) in sorted(per_scaf.items(),
                                          key=lambda kv: -(sum(kv[1][1:4]) / max(kv[1][0], 1))):
        w = n + d + rep
        print(f"  {s:<13}{runs:>5}{c:>7}{n:>7}{d:>7}{rep:>8}{100*w/max(c,1):>9.1f}%")

    print("\n  worst offenders:")
    for w, r, detail in sorted(worst, reverse=True, key=lambda x: x[0])[:6]:
        print(f"    {r['scaffolding']}/{r['model']}/{r['arm']}: {w} wasted of "
              f"{r['tool_calls']} calls, done={r.get('completion_pct')}%")
        print(f"        {', '.join(detail[:4])}")
    print()


def scaffolding_headline(rows, label):
    """The result the ratio analysis keeps burying."""
    agg = defaultdict(list)
    for r in rows:
        if not r.get("void") and r.get("total_input_tokens"):
            agg[r["scaffolding"]].append(r)
    print("=" * 76)
    print(f"SCAFFOLDING — {label}")
    print("=" * 76)
    print(f"\n  {'scaffolding':<13}{'runs':>5}{'median tok':>12}{'full done':>11}"
          f"{'MCP support':>13}")
    base = None
    for s, rs in sorted(agg.items(),
                        key=lambda kv: st.median(x["total_input_tokens"] for x in kv[1])):
        med = st.median(x["total_input_tokens"] for x in rs)
        full = sum(1 for x in rs if (x.get("completion_pct") or 0) == 100)
        mcp = "no" if s == "pi" else "yes"
        base = base or med
        print(f"  {s:<13}{len(rs):>5}{med:>12,.0f}{full:>8}/{len(rs)}{mcp:>13}"
              f"   ×{med/base:.0f}")
    print()


if __name__ == "__main__":
    for f, lab in (("runs-rerun.jsonl", "Experiment 1 (re-run)"),
                   ("runs-e3-corrected.jsonl", "Experiment 3 (corrected)")):
        if (ROOT / "results" / f).exists():
            rows = load(f)
            scaffolding_headline(rows, lab)
            report(rows, f"WASTED TOOL CALLS — {lab}")
