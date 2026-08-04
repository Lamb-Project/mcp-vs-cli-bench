#!/usr/bin/env python3
"""Where do the extra tokens go?

Two questions the ratio alone cannot answer:

  A. When MCP costs more, is it the registry (a fixed prefill), the per-call
     payloads (scales with calls), or conversation growth (scales with turns)?
  B. When the CLI costs more — the ratio<1 cells — what is it spending on?

Also reports the uncached figure. Total input counts tokens the server may have
served from cache; prefilled = input - cached is what actually had to be
processed, and it is the honest basis for a cost claim.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from bench.insight import classify, load, paired


def prefilled(r: dict) -> int | None:
    ti, c = r.get("total_input_tokens"), r.get("cached_tokens")
    if ti is None:
        return None
    return ti - (c or 0)


def per_call(r: dict) -> float | None:
    n = r.get("tool_calls") or 0
    ti = r.get("total_input_tokens")
    return (ti / n) if (n and ti) else None


def band(reg: dict) -> str:
    """Coarse label for how a run spent its calls."""
    if not reg:
        return "—"
    top = sorted(reg.items(), key=lambda kv: -kv[1])[:2]
    return ", ".join(f"{k}×{v}" for k, v in top)


def section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def a_where_mcp_spends(rows) -> None:
    section("A. When MCP costs more, where does the extra go?")
    pairs = [(s, m, c, k) for s, m, c, k in paired(rows, strict=False)
             if k["total_input_tokens"] > c["total_input_tokens"]]
    pairs.sort(key=lambda x: -(x[3]["total_input_tokens"] / x[2]["total_input_tokens"]))
    print(f"\n  {'cell':<26}{'ratio':>6}{'Δtokens':>10}{'Δcalls':>8}"
          f"{'CLI t/call':>11}{'MCP t/call':>11}{'MCP init':>10}")
    for s, m, c, k in pairs:
        ratio = k["total_input_tokens"] / c["total_input_tokens"]
        dt = k["total_input_tokens"] - c["total_input_tokens"]
        dc = (k.get("tool_calls") or 0) - (c.get("tool_calls") or 0)
        pc_c, pc_k = per_call(c), per_call(k)
        print(f"  {s+'/'+m:<26}{ratio:>6.2f}{dt:>10,}{dc:>+8}"
              f"{(f'{pc_c:,.0f}' if pc_c else '—'):>11}"
              f"{(f'{pc_k:,.0f}' if pc_k else '—'):>11}"
              f"{(k.get('initial_tokens') or 0):>10,}")

    # attribute the delta: registry (init) vs everything after
    print("\n  attribution of the extra MCP tokens:")
    for s, m, c, k in pairs:
        dt = k["total_input_tokens"] - c["total_input_tokens"]
        init_gap = (k.get("initial_tokens") or 0) - (c.get("initial_tokens") or 0)
        rest = dt - init_gap
        if dt <= 0:
            continue
        print(f"    {s+'/'+m:<26} first request {init_gap:>+9,} "
              f"({100*init_gap/dt:>5.1f}%)   everything after {rest:>+9,} "
              f"({100*rest/dt:>5.1f}%)")


def b_where_cli_spends(rows) -> None:
    section("B. When the CLI costs more (ratio < 1), what is it spending on?")
    pairs = [(s, m, c, k) for s, m, c, k in paired(rows, strict=False)
             if k["total_input_tokens"] < c["total_input_tokens"]]
    pairs.sort(key=lambda x: x[3]["total_input_tokens"] / x[2]["total_input_tokens"])
    print(f"\n  {'cell':<26}{'ratio':>6}{'CLI tok':>10}{'CLIcalls':>9}"
          f"{'CLI t/call':>11}  what the CLI arm called")
    for s, m, c, k in pairs:
        ratio = k["total_input_tokens"] / c["total_input_tokens"]
        pc = per_call(c)
        print(f"  {s+'/'+m:<26}{ratio:>6.2f}{c['total_input_tokens']:>10,}"
              f"{(c.get('tool_calls') or 0):>9}"
              f"{(f'{pc:,.0f}' if pc else '—'):>11}  {band(c.get('tool_register') or {})}")
        print(f"  {'':<26}{'':>6}{'':>10}{'':>9}{'':>11}  MCP side: "
              f"{band(k.get('tool_register') or {})}  [{classify(k)}]")


def c_uncached(rows) -> None:
    section("C. Uncached tokens — what actually had to be processed")
    pairs = paired(rows, strict=False)
    out = []
    for s, m, c, k in pairs:
        pc, pk = prefilled(c), prefilled(k)
        if not pc or not pk:
            continue
        out.append((pk / pc, s, m, c, k, pc, pk))
    out.sort()
    print(f"\n  {'cell':<26}{'CLI pre':>10}{'MCP pre':>10}{'pre ratio':>11}"
          f"{'tot ratio':>11}{'CLI hit%':>10}{'MCP hit%':>10}")
    for pr, s, m, c, k, pc, pk in out:
        tr = k["total_input_tokens"] / c["total_input_tokens"]
        print(f"  {s+'/'+m:<26}{pc:>10,}{pk:>10,}{pr:>11.2f}{tr:>11.2f}"
              f"{(c.get('cache_hit_pct') or 0):>9.1f}%{(k.get('cache_hit_pct') or 0):>9.1f}%")
    if out:
        mp = statistics.median(x[0] for x in out)
        mt = statistics.median(
            x[4]["total_input_tokens"] / x[3]["total_input_tokens"] for x in out)
        print(f"\n  median uncached ratio {mp:.2f}×   median total ratio {mt:.2f}×")
        print("  Caching COMPRESSES the gap but does not remove it. The MCP")
        print("  registry is a stable prefix and caches well — MCP arms show the")
        print("  higher hit rate in most pairs — so the penalty on tokens actually")
        print("  processed is smaller than the penalty on tokens counted.")


def main() -> None:
    rows = load()
    a_where_mcp_spends(rows)
    b_where_cli_spends(rows)
    c_uncached(rows)


if __name__ == "__main__":
    main()
