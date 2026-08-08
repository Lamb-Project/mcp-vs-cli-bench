#!/usr/bin/env python3
"""What including opencode would do to the paper's numbers.

Marc's instruction was to run the row and then decide whether it enters the
paper, so this reports the study both ways rather than assuming the answer. It
never writes a dataset.

Compares:  e4-final as published in draft 9   (six scaffoldings)
   against: e4-final + the opencode row       (seven)
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
MINIMAL = {"pi", "tau"}


def norm(r):
    rub = r.get("rubric") or {}
    valid = {k: v for k, v in rub.items() if k != "pr_links_issue"}
    if valid:
        r["completion_pct"] = round(
            100.0 * sum(bool(v) for v in valid.values()) / len(valid), 1)
    return r


def load(name):
    p = R / name
    if not p.exists():
        return []
    return [norm(json.loads(l)) for l in p.read_text().splitlines() if l.strip()]


def live(rs):
    return [r for r in rs if not r.get("void") and r.get("total_input_tokens")]


def done(rs):
    return [r for r in live(rs) if (r.get("completion_pct") or 0) == 100]


def summarise(rows, label):
    L, D = live(rows), done(rows)
    print(f"\n{'=' * 72}\n{label}: {len(rows)} cells, {len(L)} live, {len(D)} completed\n{'=' * 72}")
    g = defaultdict(list)
    for r in D:
        g[r["scaffolding"]].append(r["total_input_tokens"])
    order = sorted(g, key=lambda s: st.median(g[s]))
    base = st.median(g[order[0]])
    for s in order:
        m = st.median(g[s])
        mark = "   <-- opencode" if s == "opencode" else ""
        print(f"  {s:<12} n={len(g[s]):>2}  median={round(m):>9,}  ×{m/base:>5.1f}{mark}")
    print(f"  SPAN: ×{st.median(g[order[-1]])/base:.1f}"
          f"   (cheapest {order[0]}, dearest {order[-1]})")

    for arm in ("cli", "mcp"):
        sub = [r for r in L if r["arm"] == arm and r["scaffolding"] not in MINIMAL
               and r.get("theoretical_cost_usd") is not None]
        bad = [r for r in sub if (r.get("completion_pct") or 0) < 100]
        tot = sum(r["theoretical_cost_usd"] for r in sub)
        pct = 100 * sum(r["theoretical_cost_usd"] for r in bad) / tot if tot else 0
        print(f"  waste {arm}: {pct:>5.1f}%  ({len(bad)} failed of {len(sub)})")

    by = defaultdict(dict)
    for r in D:
        by[(r["scaffolding"], r["model"])][r["arm"]] = r["total_input_tokens"]
    pairs = sorted((v["mcp"] / v["cli"], k) for k, v in by.items()
                   if "cli" in v and "mcp" in v)
    if pairs:
        print(f"  paired ratios: {len(pairs)}  range {pairs[0][0]:.2f}–{pairs[-1][0]:.2f}"
              f"  median {st.median(p[0] for p in pairs):.2f}")
        for ratio, k in pairs:
            mark = "  <--" if k[0] == "opencode" else ""
            print(f"      {k[0]:<12}{k[1]:<14} ×{ratio:.2f}{mark}")


def main():
    published = [json.loads(l) for l in (R / "e4-final.jsonl").read_text().splitlines() if l.strip()]
    oc = (load("runs-opencode-rep1.jsonl") + load("runs-opencode-hosted.jsonl"))
    summarise(published, "AS PUBLISHED IN DRAFT 9 (six scaffoldings)")
    if not oc:
        print("\n(no opencode rows yet)")
        return
    summarise(published + oc, "WITH OPENCODE (seven scaffoldings)")

    print(f"\n{'=' * 72}\nEVERY OPENCODE RUN, all passes\n{'=' * 72}")
    allruns = oc + load("runs-opencode-rep2.jsonl") + load("runs-opencode-rep3.jsonl")
    for r in sorted(allruns, key=lambda r: (r["model"], r["arm"])):
        print(f"  {r['model']:<14}{r['arm']:<4} done={str(r.get('completion_pct')):<6}"
              f" in={str(r.get('total_input_tokens')):>8}"
              f" tools={str(r.get('tool_calls')):>3} mcp={str(r.get('mcp_tools_used')):>3}"
              f" wall={r.get('wall_s')}")
    cfg = defaultdict(list)
    for r in done(allruns):
        cfg[(r["model"], r["arm"])].append(r["total_input_tokens"])
    print("\n  run-to-run spread, completed repetitions only:")
    for k, v in sorted(cfg.items()):
        if len(v) > 1:
            print(f"    {k[0]:<14}{k[1]:<4} n={len(v)}  ×{max(v)/min(v):.2f}")


if __name__ == "__main__":
    main()
