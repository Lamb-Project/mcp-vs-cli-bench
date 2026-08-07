#!/usr/bin/env python3
"""Add theoretical_cost_usd to run records that lack it.

The runner computes this at write time; the Claude Code passes were driven by a
standalone script that did not, so their rows carry a null cost and the
wasted-cost share cannot be summed. The figure is a modelled cost at published
rates, not money spent -- local cells are priced the same way in the existing
dataset, which is what makes cost comparable across hosted and local runs.

Same formula and the same price table as bench/runner.py.
"""
from __future__ import annotations

import json
import pathlib
import sys

from bench.costs import PRICES, theoretical_cost

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"


def backfill(name: str) -> None:
    p = R / name
    if not p.exists():
        print(f"  {name:<26} (absent)")
        return
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    n = 0
    for r in rows:
        if r.get("theoretical_cost_usd") is not None:
            continue
        if not r.get("total_input_tokens") or r["model"] not in PRICES:
            continue
        r["theoretical_cost_usd"] = theoretical_cost(
            r["model"], r.get("total_input_tokens") or 0,
            r.get("total_output_tokens") or 0,
            r.get("cached_tokens") or 0).total_usd
        n += 1
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"  {name:<26} {n} row(s) priced")


def main() -> None:
    names = sys.argv[1:] or ["runs-cc-rep1.jsonl", "runs-cc-rep2.jsonl",
                             "runs-cc-rep3.jsonl"]
    missing = [m for m in ("glm-5.2", "qwen3.6:27b") if m not in PRICES]
    if missing:
        raise SystemExit(f"no published price for {missing}; the existing "
                         "dataset prices these, so the table has changed")
    for n in names:
        backfill(n)


if __name__ == "__main__":
    main()
