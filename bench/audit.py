#!/usr/bin/env python3
"""Hunt for recording faults and anomalies across a results file.

Every check here corresponds to a fault we actually shipped at some point. The
point is not to prove the data is clean — it is to make the specific ways it has
been dirty before impossible to miss again.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

from bench.insight import classify

ROOT = Path(__file__).resolve().parent.parent


def load(name: str) -> list[dict]:
    return [json.loads(l) for l in (ROOT / "results" / name).read_text().splitlines()
            if l.strip()]


def audit(rows: list[dict], label: str) -> None:
    print("=" * 74)
    print(f"AUDIT — {label}  ({len(rows)} cells)")
    print("=" * 74)
    flags = 0

    live = [r for r in rows if not r.get("void")]

    def flag(msg, items):
        nonlocal flags
        if items:
            flags += len(items)
            print(f"\n  ⚠ {msg}  ({len(items)})")
            for it in items[:8]:
                print(f"      {it}")

    # 1. impossible or missing token accounting
    flag("total_input_tokens missing on a non-void cell",
         [f"{r['scaffolding']}/{r['model']}/{r['arm']}: err={str(r.get('error'))[:40]}"
          for r in live if not r.get("total_input_tokens")])

    # 2. cached > input, or cache reported where the provider cannot report it
    flag("cached_tokens exceeds total input (impossible)",
         [f"{r['scaffolding']}/{r['model']}/{r['arm']}: "
          f"cached={r.get('cached_tokens')} > input={r.get('total_input_tokens')}"
          for r in live if (r.get("cached_tokens") or 0) > (r.get("total_input_tokens") or 0)])

    flag("cache figure absent — provider does not report it (not a zero)",
         [f"{r['scaffolding']}/{r['model']}/{r['arm']}"
          for r in live if r.get("total_input_tokens") and not r.get("cached_tokens")])

    # 3. completion without tool calls — answered from priors or register gap
    flag("scored >0% with zero recorded tool calls",
         [f"{r['scaffolding']}/{r['model']}/{r['arm']}: done={r.get('completion_pct')}"
          for r in live if (r.get("completion_pct") or 0) > 0 and not r.get("tool_calls")])

    # 4. arm did not match assignment
    flag("arm mismatch (behaviour ≠ assignment)",
         [f"{r['scaffolding']}/{r['model']}/{r['arm']} -> {classify(r)}"
          for r in live
          if (r["arm"] == "mcp" and classify(r) != "pure-mcp")
          or (r["arm"] == "cli" and classify(r) != "pure-cli")])

    # 5. delegation, whose child tokens are billed off-thread
    flag("delegated to sub-agents — totals incomplete",
         [f"{r['scaffolding']}/{r['model']}/{r['arm']}: {r.get('delegated')}"
          for r in live if r.get("delegated")])

    # 6. token-per-call outliers: a sign of huge payloads or a stuck loop
    per = [(r["total_input_tokens"] / r["tool_calls"], r) for r in live
           if r.get("tool_calls") and r.get("total_input_tokens")]
    if per:
        med = st.median(p for p, _ in per)
        flag(f"tokens/call more than 5× the median ({med:,.0f})",
             [f"{r['scaffolding']}/{r['model']}/{r['arm']}: {p:,.0f}/call, "
              f"{r['tool_calls']} calls, done={r.get('completion_pct')}"
              for p, r in sorted(per, reverse=True) if p > 5 * med])

    # 7. runaway call counts
    calls = [r.get("tool_calls") or 0 for r in live]
    if calls:
        medc = st.median(calls)
        flag(f"call count more than 4× the median ({medc:.0f}) — likely a loop",
             [f"{r['scaffolding']}/{r['model']}/{r['arm']}: {r['tool_calls']} calls, "
              f"done={r.get('completion_pct')}"
              for r in live if (r.get("tool_calls") or 0) > 4 * max(medc, 1)])

    # 8. ratios below 1 — a failure signature by the reporting rule
    by: dict = {}
    for r in live:
        by.setdefault((r["scaffolding"], r["model"]), {})[r["arm"]] = r
    subs = []
    for (s, m), a in by.items():
        c, k = a.get("cli"), a.get("mcp")
        if c and k and c.get("total_input_tokens") and k.get("total_input_tokens"):
            ratio = k["total_input_tokens"] / c["total_input_tokens"]
            if ratio < 1:
                why = ("incomplete" if (c.get("completion_pct") or 0) < 100
                       or (k.get("completion_pct") or 0) < 100 else "")
                why += (" impure" if classify(c) != "pure-cli"
                        or classify(k) != "pure-mcp" else "")
                subs.append(f"{s}/{m}: {ratio:.2f}× — {why.strip() or 'UNEXPLAINED'}")
    flag("ratio < 1 (failure signature unless explained)", subs)

    # 9. extreme ratios upward — equally suspicious
    highs = []
    for (s, m), a in by.items():
        c, k = a.get("cli"), a.get("mcp")
        if c and k and c.get("total_input_tokens") and k.get("total_input_tokens"):
            ratio = k["total_input_tokens"] / c["total_input_tokens"]
            if ratio > 10:
                highs.append(f"{s}/{m}: {ratio:.1f}× — CLI {c['total_input_tokens']:,}"
                             f" ({c.get('tool_calls')} calls, {c.get('completion_pct')}%)"
                             f" vs MCP {k['total_input_tokens']:,}"
                             f" ({k.get('tool_calls')} calls, {k.get('completion_pct')}%)")
    flag("ratio > 10× — check for a stalled or truncated arm", highs)

    print(f"\n  {flags} flagged observations in {label}\n")


if __name__ == "__main__":
    for name, label in (("runs-rerun.jsonl", "Experiment 1 (re-run, uniform routing)"),
                        ("runs-e3.jsonl", "Experiment 3 (private fixture, isolated)")):
        if (ROOT / "results" / name).exists():
            audit(load(name), label)
