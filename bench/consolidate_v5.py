#!/usr/bin/env python3
"""Build the single Experiment-3 dataset draft 5 reports from.

Completion is scored on the four valid rubric items throughout: pr_links_issue
is unsatisfiable by construction, because the per-run fixture reset mints a new
issue number after the check's expected value is fixed.
"""
from __future__ import annotations
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
SOURCES = ["runs-e3-corrected.jsonl", "runs-tau.jsonl", "runs-hermes.jsonl"]


def load(name):
    p = R / name
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def norm(r):
    rub = r.get("rubric") or {}
    valid = {k: v for k, v in rub.items() if k != "pr_links_issue"}
    if valid:
        r["completion_pct"] = round(100.0 * sum(bool(v) for v in valid.values()) / len(valid), 1)
    return r


def main():
    rows, seen = [], set()
    for src in SOURCES:
        for r in load(src):
            key = (r["scaffolding"], r["model"], r["arm"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(norm(r))
    out = R / "e3-final.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    live = [r for r in rows if not r.get("void")]
    print(f"{len(rows)} cells -> {out.name}  ({len(live)} live, {len(rows)-len(live)} void)")
    for s in sorted({r["scaffolding"] for r in rows}):
        n = [r for r in live if r["scaffolding"] == s]
        done = sum(1 for r in n if (r.get("completion_pct") or 0) == 100)
        print(f"  {s:<12} {len(n):>2} live, {done} complete")


if __name__ == "__main__":
    main()
