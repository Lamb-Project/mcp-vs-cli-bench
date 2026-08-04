#!/usr/bin/env python3
"""Run the benchmark matrix and write one JSONL record per cell.

Ordering is deliberate. Local inference here persists its KV cache to disk
across runs, so whichever arm runs after a similar one starts warm and looks
dramatically cheaper. Runs are therefore interleaved by arm and the cache state
is recorded per run rather than assumed away.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from bench.adapters.impl import ADAPTERS, LOCAL_MODELS
from bench.budget import check as budget_check, spent_usd
from bench.costs import PRICES, PRICES_CAPTURED, theoretical_cost

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
MCP_BIN = str(ROOT / "bin" / "github-mcp-server")

# sol dropped: 60% of Experiment 1's spend from 12% of its tokens — the worst
# information per dollar in the set. The 5.x line was substitution coverage while
# 5.6 looked unreachable and is not needed now.
OPENAI_MODELS = ["gpt-5.6-luna", "gpt-5.6-terra"]
LOCAL = ["glm-5.2", "qwen3.6:27b"]
# fable dropped at $10/$50 per million; the three Anthropic models behaved
# alike in Experiment 1, so one representative carries the per-turn telemetry.
ANTHROPIC = ["sonnet-5"]

MATRIX: dict[str, list[str]] = {
    "claude-code": ANTHROPIC,                 # cannot reach non-Anthropic endpoints
    "codex":       OPENAI_MODELS + LOCAL,
    "qwen-code":   OPENAI_MODELS + LOCAL,
    "pi":          OPENAI_MODELS + LOCAL,     # MCP arm is void; CLI arm runs
}
ARMS = ("cli", "mcp")

# Observed on the pilot workflow; used only for the pre-flight estimate.
EST_INPUT = {"mcp": 174_000, "cli": 28_000}
EST_OUTPUT = 1_100


def gh_token() -> str:
    return subprocess.run(["gh", "auth", "token"], capture_output=True,
                          text=True, check=True).stdout.strip()


def estimate() -> float:
    """Estimated real spend. Local models and subscription-billed models are $0
    of marginal spend; only metered API cells cost money."""
    total = 0.0
    rows = []
    for scaffolding, models in MATRIX.items():
        adapter = ADAPTERS[scaffolding]
        for model in models:
            for arm in ARMS:
                if arm == "mcp" and not adapter.supports_mcp:
                    continue
                if model in LOCAL_MODELS:
                    continue                      # local hardware, no spend
                if scaffolding == "claude-code":
                    continue                      # subscription, not metered here
                c = theoretical_cost(model, EST_INPUT[arm], EST_OUTPUT)
                total += c.total_usd
                rows.append((scaffolding, model, arm, c.total_usd))
    rows.sort(key=lambda r: -r[3])
    print(f"--- pre-flight spend estimate (prices captured {PRICES_CAPTURED}) ---")
    for s, m, a, c in rows[:10]:
        print(f"  {s:<11} {m:<14} {a:<4} ${c:6.3f}")
    if len(rows) > 10:
        print(f"  ... and {len(rows)-10} more metered cells")
    print(f"  ESTIMATED TOTAL SPEND: ${total:.2f}  ({len(rows)} metered cells)")
    return total


def clear_kv_cache() -> None:
    """Drop persisted llama-server slots so local arms start from a known state."""
    p = Path.home() / ".glm-kv"
    if p.exists():
        for f in p.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=5.0)
    ap.add_argument("--estimate-only", action="store_true")
    ap.add_argument("--only", help="substring filter on scaffolding or model")
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    est = estimate()
    if args.estimate_only:
        return
    if est > args.budget:
        raise SystemExit(f"estimate ${est:.2f} exceeds budget ${args.budget:.2f} — "
                         "narrow the matrix or raise --budget explicitly")

    RESULTS.mkdir(exist_ok=True)
    out = Path(args.out) if args.out else RESULTS / "runs.jsonl"
    token = gh_token()
    workdir = RESULTS / "runs"
    workdir.mkdir(parents=True, exist_ok=True)

    # arm-major interleave: every scaffolding/model sees CLI then MCP in turn,
    # so cache warmth cannot align with one arm
    # void cells are RUN (and immediately returned void) rather than skipped, so
    # they appear in the results table -- "cannot" and "costs nothing" are
    # different claims and the table has to be able to say which
    cells = [(s, m, a) for a in ARMS for s, ms in MATRIX.items() for m in ms]
    if args.only:
        cells = [c for c in cells if args.only in c[0] or args.only in c[1]]

    print(f"\nrunning {len(cells)} cells -> {out}")
    print(f"metered spend so far: ${spent_usd():.2f} of ${args.budget:.2f}")
    for i, (scaffolding, model, arm) in enumerate(cells, 1):
        if model not in LOCAL_MODELS:
            budget_check(args.budget)     # refuse to start a breaching cell
        # The task writes, so a previous run's branch or PR would satisfy this
        # run's checks. Reset before every cell.
        subprocess.run(["python3", "-m", "bench.seed_e2"],
                       cwd=str(ROOT), capture_output=True,
                       env={**os.environ, "PYTHONPATH": str(ROOT)})
        if model in LOCAL_MODELS:
            clear_kv_cache()
        adapter = ADAPTERS[scaffolding](workdir, MCP_BIN, token)
        t0 = time.time()
        print(f"[{i}/{len(cells)}] {scaffolding} / {model} / {arm} ...", flush=True)
        res = adapter.run(model, arm, timeout=args.timeout)
        if res.total_input_tokens and model in PRICES:
            res.theoretical_cost_usd = theoretical_cost(
                model, res.total_input_tokens or 0, res.total_output_tokens or 0,
                res.cached_tokens or 0).total_usd
        with out.open("a") as fh:
            fh.write(res.to_json() + "\n")
        flag = "VOID" if res.void else (res.error or f"{res.completion_pct}%")
        print(f"      -> {flag}  tools={res.tool_calls} "
              f"in={res.total_input_tokens} cache={res.cache_hit_pct}% "
              f"({round(time.time()-t0)}s)", flush=True)


if __name__ == "__main__":
    main()
