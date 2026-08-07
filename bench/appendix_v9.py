#!/usr/bin/env python3
"""Emit Appendix A — every individual run — from the dataset.

The appendix was maintained by hand, which is why it still listed 42 runs and a
Claude Code MCP cell that has since been voided, in a draft whose tables had
moved on. A per-run table is exactly the artifact that should never be typed:
it is long, it is dull to check, and a reader who does check it is checking the
paper's honesty.

Writes the two tables (MCP-capable, then catalogue-free) to stdout for pasting
under the Appendix A heading.
"""
from __future__ import annotations

import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASET = os.environ.get("BENCH_DATASET", "e4-final.jsonl")
MINIMAL = {"pi", "tau"}
SHORT_SCAF = {"claude-code": "claude", "qwen-code": "qwen"}
SHORT_MODEL = {"gpt-5.6-luna": "luna", "gpt-5.6-terra": "terra",
               "qwen3.6:27b": "qwen27b", "sonnet-5": "sonnet"}
HEADER = ("| Harness | Model | Arm | Tokens | Cache | Calls | Schemas | Done |\n"
          "|---|---|:--:|---:|---:|---:|---:|---:|")


def schemas(r):
    """Tool descriptions transmitted per request, where the scaffolding said."""
    n = r.get("schemas_per_request")
    if n:
        return str(n)
    # Recorded for Hermes during the run; measured at the proxy for Claude Code.
    if r["scaffolding"] == "hermes":
        return "7" if r["arm"] == "mcp" else "6"
    if r["scaffolding"] == "claude-code" and r["model"] not in ("sonnet-5",):
        return "74" if r["arm"] == "mcp" else "27"
    return "—"


def row(r):
    if r.get("void"):
        # Two different things get voided and the table must not merge them: a
        # cell that cannot exist (no MCP client) and a cell that ran and was
        # discarded (the credential fault of Section 2.6). "Cannot be run",
        # "costs nothing" and "was run and thrown away" are three statements.
        why = r.get("void_reason") or ""
        label = "discarded" if "401" in why else "void"
        return (f"| {SHORT_SCAF.get(r['scaffolding'], r['scaffolding'])} "
                f"| {SHORT_MODEL.get(r['model'], r['model'])} | {r['arm']} "
                f"| {label} | | | | |")
    cache = ("—" if r.get("cached_tokens") is None
             else f"{round(100*r['cached_tokens']/max(1, r['total_input_tokens']))}%")
    calls = r.get("tool_calls") if r.get("tool_register") else "—"
    done = "—" if r.get("completion_pct") is None else f"{round(r['completion_pct'])}%"
    return (f"| {SHORT_SCAF.get(r['scaffolding'], r['scaffolding'])} "
            f"| {SHORT_MODEL.get(r['model'], r['model'])} | {r['arm']} "
            f"| {r['total_input_tokens']:,} | {cache} | {calls} "
            f"| {schemas(r)} | {done} |")


def main():
    rows = [json.loads(l) for l in
            (ROOT / "results" / DATASET).read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: (r["scaffolding"], r["model"], r["arm"]))
    print(f"The tables below list all {len(rows)} runs.\n")
    for label, sel in (("**MCP-capable harnesses**",
                        lambda r: r["scaffolding"] not in MINIMAL),
                       ("**Harnesses with no MCP client**",
                        lambda r: r["scaffolding"] in MINIMAL)):
        print(label + "\n")
        print(HEADER)
        for r in rows:
            if sel(r):
                print(row(r))
        print()


if __name__ == "__main__":
    main()
