#!/usr/bin/env python3
"""Analysis proper: answer questions, do not dump tables.

Four questions, in order of importance:

  Q0  Did each run actually use only the method it was assigned? Nothing else
      means anything until this is settled.
  Q1  Holding scaffolding and model fixed, which surface costs fewer tokens?
  Q2  Does one surface complete the task where the other does not?
  Q3  What path did each scaffolding take, and does orchestration pay for
      itself on a task this small?
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import os
DATA = pathlib_Path = ROOT / "results" / os.environ.get("BENCH_DATA", "final.jsonl")
RUNS = ROOT / "results" / "runs"

SHELL_HINT = ("shell", "bash", "run_shell_command", "Bash", "execute")
# A third path nobody designed for: several agents ignored both surfaces and
# fetched api.github.com over HTTP. Counting these as "no tools" hid them; both
# arms were silently contaminated by a method that is neither.
WEB_HINT = ("web_fetch", "WebFetch", "fetch", "curl")
ORCHESTRATION = ("delegate:", "spawn_agent", "create_sub_session", "agent",
                 "Task", "tool_search", "ToolSearch")


def load() -> list[dict]:
    return [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]


def classify(r: dict) -> str:
    """What the run ACTUALLY used, from its tool register — not what it was told
    to use. An MCP arm that completed through the shell is a CLI run wearing an
    MCP label, and averaging it into the MCP column corrupts the comparison."""
    if r.get("void"):
        return "void"
    reg = r.get("tool_register") or {}
    mcp = sum(n for k, n in reg.items() if k.startswith(("mcp__", "mcp_")))
    web = sum(n for k, n in reg.items() if any(h in k for h in WEB_HINT))
    shell = sum(n for k, n in reg.items()
                if any(h in k for h in SHELL_HINT)
                and not k.startswith("mcp")
                and not any(h in k for h in WEB_HINT))
    used = sum(1 for x in (mcp, shell, web) if x)
    if used > 1:
        return "mixed"
    if mcp:
        return "pure-mcp"
    if shell:
        return "pure-cli"
    if web:
        return "web-api"        # bypassed both surfaces entirely
    return "no-tools"


def orchestration_calls(r: dict) -> int:
    reg = r.get("tool_register") or {}
    return sum(n for k, n in reg.items()
               if any(o in k for o in ORCHESTRATION))


def q0_purity(rows: list[dict]) -> None:
    print("=" * 72)
    print("Q0  Did each run use exclusively the method it was assigned?")
    print("=" * 72)
    counts: dict[tuple[str, str], int] = defaultdict(int)
    offenders = []
    for r in rows:
        c = classify(r)
        counts[(r["arm"], c)] += 1
        if r["arm"] == "mcp" and c in ("pure-cli", "mixed", "web-api", "no-tools"):
            offenders.append((r, c))
        if r["arm"] == "cli" and c in ("pure-mcp", "mixed", "web-api"):
            offenders.append((r, c))
    for arm in ("cli", "mcp"):
        line = ", ".join(f"{k[1]}={v}" for k, v in sorted(counts.items())
                         if k[0] == arm)
        print(f"  assigned {arm.upper():<4}: {line}")
    print()
    if offenders:
        print("  Runs whose actual behaviour does not match their assignment:")
        for r, c in offenders:
            reg = ", ".join(f"{k}×{v}" for k, v in
                            sorted((r.get('tool_register') or {}).items(),
                                   key=lambda kv: -kv[1])[:3])
            print(f"    {r['scaffolding']}/{r['model']}/{r['arm']:<3} -> {c:<9} [{reg}]")
    else:
        print("  none — every run used only its assigned surface")
    return offenders


def paired(rows: list[dict], strict: bool):
    """Pairs where both arms exist. strict=True keeps only pairs where each run
    used exclusively its assigned method."""
    by: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for r in rows:
        if r.get("void"):
            continue
        by[(r["scaffolding"], r["model"])][r["arm"]] = r
    out = []
    for (s, m), arms in sorted(by.items()):
        c, k = arms.get("cli"), arms.get("mcp")
        if not (c and k):
            continue
        if c.get("totals_incomplete") or k.get("totals_incomplete"):
            continue
        if not (c.get("total_input_tokens") and k.get("total_input_tokens")):
            continue
        if strict:
            # A ratio is meaningful only when both arms finished the task AND
            # each used only its assigned surface. Every sub-1.0 ratio observed
            # so far was one or the other failing: an incomplete run burning
            # tokens on flailing, or an arm that was not the arm it claimed.
            if classify(c) != "pure-cli" or classify(k) != "pure-mcp":
                continue
            if (c.get("completion_pct") or 0) < 100 or (k.get("completion_pct") or 0) < 100:
                continue
        out.append((s, m, c, k))
    return out


def q1_tokens(rows: list[dict]) -> None:
    print()
    print("=" * 72)
    print("Q1  Holding scaffolding and model fixed, which surface costs less?")
    print("=" * 72)
    for strict, label in ((False, "all pairs with both arms"),
                          (True, "pairs where BOTH runs were method-pure")):
        pairs = paired(rows, strict)
        if not pairs:
            print(f"  {label}: none")
            continue
        ratios = [(k["total_input_tokens"] / c["total_input_tokens"], s, m, c, k)
                  for s, m, c, k in pairs]
        ratios.sort()
        med = statistics.median(r[0] for r in ratios)
        cheaper_cli = sum(1 for r in ratios if r[0] > 1)
        print(f"\n  {label}  (n={len(ratios)})")
        print(f"    median MCP/CLI = {med:.2f}×   "
              f"CLI cheaper in {cheaper_cli}/{len(ratios)} pairs")
        print(f"    range {ratios[0][0]:.2f}×–{ratios[-1][0]:.2f}×")
        for ratio, s, m, c, k in ratios:
            arrow = "MCP cheaper" if ratio < 1 else ""
            print(f"      {s+'/'+m:<26} {c['total_input_tokens']:>8,} -> "
                  f"{k['total_input_tokens']:>8,}  {ratio:>5.2f}×  {arrow}")


def q2_completion(rows: list[dict]) -> None:
    print()
    print("=" * 72)
    print("Q2  Does one surface complete the task where the other does not?")
    print("=" * 72)
    pairs = paired(rows, strict=True)
    both, only_cli, only_mcp, neither = 0, [], [], 0
    for s, m, c, k in pairs:
        cc = (c.get("completion_pct") or 0) == 100
        kk = (k.get("completion_pct") or 0) == 100
        if cc and kk:
            both += 1
        elif cc:
            only_cli.append(f"{s}/{m}")
        elif kk:
            only_mcp.append(f"{s}/{m}")
        else:
            neither += 1
    print(f"  method-pure pairs: {len(pairs)}")
    print(f"    both surfaces completed fully : {both}")
    print(f"    only CLI completed            : {len(only_cli)}  {only_cli}")
    print(f"    only MCP completed            : {len(only_mcp)}  {only_mcp}")
    print(f"    neither                       : {neither}")


def q3_paths(rows: list[dict]) -> None:
    print()
    print("=" * 72)
    print("Q3  What path does each scaffolding take, and does orchestration pay?")
    print("=" * 72)
    agg: dict[str, list] = defaultdict(list)
    for r in rows:
        if r.get("void") or not r.get("total_input_tokens"):
            continue
        agg[r["scaffolding"]].append(r)
    print(f"\n  {'scaffolding':<13}{'runs':>5}{'med tokens':>12}{'med calls':>10}"
          f"{'orch calls':>11}{'full done':>10}")
    for s, rs in sorted(agg.items(),
                        key=lambda kv: statistics.median(
                            x["total_input_tokens"] for x in kv[1])):
        toks = statistics.median(x["total_input_tokens"] for x in rs)
        calls = statistics.median(x.get("tool_calls") or 0 for x in rs)
        orch = sum(orchestration_calls(x) for x in rs)
        done = sum(1 for x in rs if (x.get("completion_pct") or 0) == 100)
        print(f"  {s:<13}{len(rs):>5}{toks:>12,.0f}{calls:>10.0f}{orch:>11}"
              f"{done:>7}/{len(rs)}")

    print("\n  Same model, every scaffolding, CLI arm only:")
    per: dict[str, list] = defaultdict(list)
    for r in rows:
        if r.get("void") or r["arm"] != "cli" or not r.get("total_input_tokens"):
            continue
        per[r["model"]].append(r)
    for m, rs in sorted(per.items()):
        if len(rs) < 3:
            continue
        rs.sort(key=lambda x: x["total_input_tokens"])
        lo, hi = rs[0], rs[-1]
        print(f"    {m:<15} {lo['scaffolding']:>11} {lo['total_input_tokens']:>8,}"
              f"   ...{hi['scaffolding']:>11} {hi['total_input_tokens']:>8,}"
              f"   ×{hi['total_input_tokens']/lo['total_input_tokens']:.0f}")


def main() -> None:
    rows = load()
    q0_purity(rows)
    q1_tokens(rows)
    q2_completion(rows)
    q3_paths(rows)


if __name__ == "__main__":
    main()
