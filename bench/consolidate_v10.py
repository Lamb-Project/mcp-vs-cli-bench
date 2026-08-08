#!/usr/bin/env python3
"""Build the dataset draft 10 reports from: Experiment 3 plus the Claude Code row.

Draft 8 measured Claude Code on Anthropic models only, from the scaffolding's own
usage record, because the harness assumed it could not be pointed anywhere else.
It can: ANTHROPIC_BASE_URL redirects it at any endpoint speaking the Anthropic
message format, which the LiteLLM proxy serves. The cells added here run Claude
Code against the same local models as every other scaffolding, measured at the
proxy like every other scaffolding.

Completion is scored on the four valid rubric items throughout, exactly as
consolidate_v5 does: pr_links_issue is unsatisfiable by construction, because the
per-run fixture reset mints a new issue number after the check's expected value
is fixed. Scoring the new rows over five items instead would have marked every
genuinely complete run 80% and dropped it from the completed-only conditioning
that every headline number depends on.
"""
from __future__ import annotations
import json
import pathlib

from bench.costs import PRICES, theoretical_cost

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"

# The Claude Code row runs three times, like the other local cells. e3-final
# carries one row per cell and the repetitions live in their own files feeding
# the variance analysis, so pass 1 is the representative here and passes 2 and 3
# are read separately by the replication section.
#
# Listed first: where it overlaps the older files on (scaffolding, model, arm) it
# is the better measurement -- proxy-side rather than self-reported, and with an
# MCP credential that actually authenticates.
SOURCES = ["runs-cc-sonnet-mcp.jsonl", "runs-cc-rep1.jsonl",
           "runs-opencode-rep1.jsonl", "runs-opencode-hosted.jsonl",
           "runs-e3-corrected.jsonl", "runs-tau.jsonl", "runs-hermes.jsonl"]


def load(name):
    p = R / name
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def norm(r):
    rub = r.get("rubric") or {}
    valid = {k: v for k, v in rub.items() if k != "pr_links_issue"}
    if valid:
        r["completion_pct"] = round(
            100.0 * sum(bool(v) for v in valid.values()) / len(valid), 1)
    # The draft-8 Claude Code MCP cell answered 401 to every call because of the
    # credential fault, and an earlier pass voided it. Voiding was the wrong
    # response: a run that failed on setup was never a test of the protocol, so
    # discarding it removes a data point rather than a bad one. It has been
    # re-run with a working credential -- runs-cc-sonnet-mcp.jsonl, listed first
    # in SOURCES so it wins the dedupe -- and it completes.
    # Price here rather than afterwards. e3-final carries costs that
    # consolidate_v5 never wrote, so they were added by a step outside the
    # pipeline and the dataset could not be rebuilt from its sources in one
    # command. Same formula and table as bench/runner.py.
    if (r.get("theoretical_cost_usd") is None and r.get("total_input_tokens")
            and r.get("model") in PRICES):
        r["theoretical_cost_usd"] = theoretical_cost(
            r["model"], r.get("total_input_tokens") or 0,
            r.get("total_output_tokens") or 0,
            r.get("cached_tokens") or 0).total_usd
    # Table 4's second cost column, priced with cached reads at a tenth. The
    # 0.9 rate is not a guess: it is the value that reproduces the stored
    # figures in e3-final exactly (1.115388 -> 0.165660 on the Claude Code
    # command-line cell).
    if (r.get("cost_usd_cached_discounted") is None
            and r.get("total_input_tokens") and r.get("model") in PRICES):
        r["cost_usd_cached_discounted"] = theoretical_cost(
            r["model"], r.get("total_input_tokens") or 0,
            r.get("total_output_tokens") or 0,
            r.get("cached_tokens") or 0, cache_discount=0.9).total_usd
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
    out = R / "e5-final.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    live = [r for r in rows if not r.get("void")]
    print(f"{len(rows)} cells -> {out.name}  "
          f"({len(live)} live, {len(rows)-len(live)} void)")
    for s in sorted({r["scaffolding"] for r in rows}):
        n = [r for r in live if r["scaffolding"] == s]
        done = sum(1 for r in n if (r.get("completion_pct") or 0) == 100)
        models = sorted({r["model"] for r in rows if r["scaffolding"] == s})
        print(f"  {s:<12} {len(n):>2} live, {done} complete   {', '.join(models)}")


if __name__ == "__main__":
    main()
