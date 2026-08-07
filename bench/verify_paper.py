#!/usr/bin/env python3
"""Recompute every number the paper claims, straight from the raw dataset.

Written to be independent of figures_v5.py rather than to share code with it: a
shared helper that is wrong produces a table and a figure that agree with each
other and disagree with reality. Everything here is recomputed from
e3-final.jsonl and compared against the values written into the manuscript.
"""
from __future__ import annotations
import json, os, pathlib, re, statistics as st
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Both drafts stay checkable: v8 against e3-final by default, v9 against
# e4-final by setting BENCH_PAPER and BENCH_DATASET. A verifier that can only
# check the current draft cannot show that the previous one was sound.
PAPER = pathlib.Path(os.environ.get(
    "BENCH_PAPER",
    str(pathlib.Path.home() / "Documents/ludo-claude/ludo-writting-workshop"
        "/writting-projects/papers/2026/mcp-vs-cli-benchmark/paper-draft-v8.md")))
DATASET = os.environ.get("BENCH_DATASET", "e3-final.jsonl")
MINIMAL = {"pi", "tau"}
fails, checks = [], 0


def rows():
    return [json.loads(l) for l in (ROOT / "results" / DATASET).read_text().splitlines() if l.strip()]


def live(rs):
    return [r for r in rs if not r.get("void") and r.get("total_input_tokens")]


def completed(rs):
    return [r for r in live(rs) if (r.get("completion_pct") or 0) == 100]


def ck(label, got, want, tol=0.0):
    global checks
    checks += 1
    ok = (abs(got - want) <= tol) if isinstance(want, (int, float)) else got == want
    if not ok:
        fails.append(f"{label}: paper says {want}, data gives {got}")
    print(f"  {'OK ' if ok else 'FAIL'}  {label:<52} paper={want:<12} data={got}")


def main():
    rs = rows(); L = live(rs); D = completed(rs)
    txt = PAPER.read_text()

    print("=" * 78, "\nTABLE 1 — all arms, by scaffolding\n", "=" * 78, sep="")
    agg, cmp = defaultdict(list), defaultdict(list)
    for r in L: agg[r["scaffolding"]].append(r)
    for r in D: cmp[r["scaffolding"]].append(r)
    order = sorted(cmp, key=lambda s: st.median(x["total_input_tokens"] for x in cmp[s]))
    base = st.median(x["total_input_tokens"] for x in cmp[order[0]])
    disp = {"claude-code": "Claude Code", "qwen-code": "qwen-code", "codex": "Codex",
            "hermes": "Hermes", "tau": "Tau", "pi": "pi"}
    for s2 in order:
        med = st.median(x["total_input_tokens"] for x in cmp[s2])
        cost = st.median(x["theoretical_cost_usd"] for x in cmp[s2])
        m = re.search(rf"\|\s*{re.escape(disp[s2])}\s*\|[^|]*\|\s*(\d+)/(\d+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*×([\d.]+)\s*\|\s*\$([\d.]+)\s*\|", txt)
        if not m:
            fails.append(f"Table 1 row for {disp[s2]} not found"); continue
        ck(f"T1 {s2} completed", len(cmp[s2]), int(m.group(1)))
        ck(f"T1 {s2} attempted", len(agg[s2]), int(m.group(2)))
        ck(f"T1 {s2} median tokens", round(med), int(m.group(3).replace(",", "")))
        out = st.median(x["total_output_tokens"] for x in cmp[s2])
        ck(f"T1 {s2} median output", round(out), int(m.group(4).replace(",", "")))
        ck(f"T1 {s2} relative", round(med/base, 1), float(m.group(5)), 0.05)
        ck(f"T1 {s2} cost", round(cost, 4), float(m.group(6)), 0.0001)

    print("\n" + "=" * 78, "\nTABLE 2 — command-line arm only\n", "=" * 78, sep="")
    cli = defaultdict(list)
    for r in L:
        if r["arm"] == "cli": cli[r["scaffolding"]].append(r)
    pibase = st.median(x["total_input_tokens"] for x in cli["pi"])
    for s in sorted(cli, key=lambda s: st.median(x["total_input_tokens"] for x in cli[s])):
        med = st.median(x["total_input_tokens"] for x in cli[s])
        done = sum(1 for x in cli[s] if (x.get("completion_pct") or 0) == 100)
        ch = [x["cache_hit_pct"] for x in cli[s] if x.get("cache_hit_pct") is not None]
        print(f"  {s:<12} n={len(cli[s])} median={med:>9,.0f} ×{med/pibase:>5.1f} "
              f"cache={(f'{st.median(ch):.0f}%' if ch else 'n/a'):>5} done={done}/{len(cli[s])}")

    print("\n" + "=" * 78, "\nTABLE 3 — arms within MCP-capable scaffoldings\n", "=" * 78, sep="")
    by = defaultdict(dict)
    for r in L: by[r["scaffolding"]].setdefault(r["arm"], []).append(r)
    for s in [x for x in by if "mcp" in by[x] and "cli" in by[x]]:
        c = st.median(x["total_input_tokens"] for x in by[s]["cli"])
        k = st.median(x["total_input_tokens"] for x in by[s]["mcp"])
        print(f"  {s:<12} cli={c:>9,.0f} mcp={k:>9,.0f} ratio=×{k/c:.2f}")

    print("\n" + "=" * 78, "\nTABLE 4 — cache, MCP-capable scaffoldings only\n", "=" * 78, sep="")
    for arm in ("cli", "mcp"):
        sub = [r for r in L if r["arm"] == arm and r["scaffolding"] not in MINIMAL]
        ch = [r["cache_hit_pct"] for r in sub if r.get("cache_hit_pct") is not None]
        # absent cache figure is not zero cached; excluded from BOTH statistics
        withc = [r for r in sub if r.get("cache_hit_pct") is not None]
        unc = [r["total_input_tokens"] - (r.get("cached_tokens") or 0) for r in withc]
        print(f"  {arm:<4} runs={len(sub)} cache_reported={len(withc)} "
              f"median_cache={st.median(ch):.0f}% median_uncached={st.median(unc):,.0f}")

    print("\n" + "=" * 78, "\nTABLE 6 — the 27B model\n", "=" * 78, sep="")
    q = sorted([r for r in L if r["model"] == "qwen3.6:27b"],
               key=lambda r: r["total_input_tokens"])
    qb = q[0]["total_input_tokens"]
    for r in q:
        print(f"  {r['scaffolding']:<12} {r['arm']:<4} {r['total_input_tokens']:>10,} "
              f"×{r['total_input_tokens']/qb:>6.1f} done={r.get('completion_pct')}%")

    print("\n" + "=" * 78, "\nSTATED SCOPE\n", "=" * 78, sep="")
    # A claim about how much was measured is as checkable as any ratio, and is
    # the kind that survives revision after the thing it describes has changed.
    models = sorted({r["model"] for r in rs})
    scaf = sorted({r["scaffolding"] for r in rs})
    for word, n in (("five", 5), ("six", 6)):
        pass
    import re as _re
    m = _re.search(r"across six agent scaffoldings and (\w+) language models", txt)
    WORDS = {"three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
    ck("distinct models claimed", len(models), WORDS.get(m.group(1), -1) if m else -1)
    ck("distinct scaffoldings claimed", len(scaf), 6)
    # Read from the manuscript rather than pinned to a constant: a check whose
    # expected value is hardcoded stops comparing the paper to the data and
    # starts comparing the data to last draft's number.
    m = _re.search(r"main matrix of (\d+) cells", txt)
    ck("total cells in dataset", len(rs), int(m.group(1)) if m else -1)

    # delivery method, completed-only (Table 5)
    ond = [r["total_input_tokens"] for r in D if r["arm"] == "mcp" and r["scaffolding"] == "hermes"]
    inl = [r["total_input_tokens"] for r in D if r["arm"] == "mcp" and r["scaffolding"] in ("codex", "qwen-code", "claude-code")]
    t5 = _re.search(r"\|\s*Fetched on demand\s*\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|\s*(\d+)\s*\|"
                    r"\s*\n\|\s*Sent in full every request\s*\|\s*(\d+)\s*\|\s*([\d,]+)\s*\|\s*(\d+)\s*\|", txt)
    ck("T5 on-demand median", round(st.median(ond)),
       int(t5.group(2).replace(",", "")) if t5 else -1)
    ck("T5 on-demand n", len(ond), int(t5.group(3)) if t5 else -1)
    ck("T5 inline median", round(st.median(inl)),
       int(t5.group(5).replace(",", "")) if t5 else -1)
    ck("T5 inline n", len(inl), int(t5.group(6)) if t5 else -1)
    m = _re.search(r"The difference is a factor of \*\*([\d.]+)\*\*", txt)
    ck("T5 ratio", round(st.median(inl)/st.median(ond), 1),
       float(m.group(1)) if m else -1, 0.05)

    print("\n" + "=" * 78, "\nHEADLINE CLAIMS\n", "=" * 78, sep="")
    span = st.median(x["total_input_tokens"] for x in cmp[order[-1]]) / base
    m = re.search(r"a factor of \*\*(\d+)\*\*", txt)
    ck("scaffolding span (completed runs)", round(span), int(m.group(1)) if m else -1, 1)
    ck("139x bonsai ratio", round(q[-1]["total_input_tokens"]/qb), 139, 1)
    # waste: the claim that does not depend on conditioning. Both shares are read
    # off Table 6 rather than pinned, so the check fails when the table and the
    # data drift apart -- which is the whole job.
    t6 = _re.search(r"\|\s*Command-line arm\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*([\d.]+)%\s*\|"
                    r"\s*\n\|\s*MCP arm\s*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*([\d.]+)%\s*\|", txt)
    for arm, grp in (("cli", 1), ("mcp", 2)):
        sub = [r for r in L if r["arm"] == arm and r["scaffolding"] not in MINIMAL]
        bad = [r for r in sub if (r.get("completion_pct") or 0) < 100]
        pct = 100*sum(r["theoretical_cost_usd"] for r in bad)/sum(r["theoretical_cost_usd"] for r in sub)
        ck(f"wasted cost share, {arm}", round(pct, 1),
           float(t6.group(grp)) if t6 else -1, 0.05)
    print(f"\n  {checks} checks, {len(fails)} failures")
    for f in fails: print(f"    ✗ {f}")


if __name__ == "__main__":
    main()
