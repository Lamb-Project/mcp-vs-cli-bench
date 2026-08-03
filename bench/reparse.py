#!/usr/bin/env python3
"""Re-derive results from saved run output, without re-running any cell.

Every run's raw stdout is kept, so a parser fix can be applied retroactively.
That matters here because parser gaps have twice produced a zero where the truth
was "not recognised" — and re-running to fix a parser would cost money and change
the cache state we control for.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from bench.adapters.base import RunResult
from bench.adapters.impl import ADAPTERS
from bench.costs import PRICES, theoretical_cost

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "results" / "runs.jsonl")
    out = src.with_suffix(".reparsed.jsonl")
    rows, changed = [], 0
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        old = json.loads(line)
        d = ROOT / "results" / "runs" / (
            f"{old['scaffolding']}__{old['model'].replace(':', '-')}__{old['arm']}")
        stdout = d / "stdout.txt"
        if old.get("void") or not stdout.exists():
            rows.append(old)
            continue
        adapter = ADAPTERS[old["scaffolding"]](d.parent, "", "")
        res = RunResult(old["scaffolding"], old["model"], old["arm"])
        res.wall_s = old.get("wall_s")
        try:
            res = adapter.parse(stdout.read_text(), "", res)
            res.assert_mcp()
            res = res.finalise()
        except Exception as exc:  # noqa: BLE001
            res.error = f"reparse failed: {exc}"
        if res.total_input_tokens and old["model"] in PRICES:
            res.theoretical_cost_usd = theoretical_cost(
                old["model"], res.total_input_tokens or 0,
                res.total_output_tokens or 0, res.cached_tokens or 0).total_usd
        new = json.loads(res.to_json())
        if new.get("tool_calls") != old.get("tool_calls"):
            changed += 1
            print(f"  {old['scaffolding']}/{old['model']}/{old['arm']}: "
                  f"tools {old.get('tool_calls')} -> {new.get('tool_calls')}")
        rows.append(new)
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"re-derived {len(rows)} rows ({changed} changed) -> {out}")


if __name__ == "__main__":
    main()
