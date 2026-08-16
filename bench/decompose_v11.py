#!/usr/bin/env python3
"""Per-run request counts from the proxy logs, and the Section-4 decomposition.

Attribution is by exact sum: the runner was strictly sequential, so a run's
requests are a contiguous same-model block in one usage log whose prompt_tokens
sum to the run's recorded total exactly. 34 of 37 proxied runs match uniquely
with zero ambiguity. The two pi runs whose sessions predate the surviving logs
are estimated as tool_calls + 1 (one request per turn plus the closing turn),
a rule validated against pi's two exactly-matched runs before use. The two
subscription Claude Code cells self-report totals only and are excluded.

Output: results/requests-per-run.jsonl (one row per attributed run) and the
two decomposition tables printed for the paper.
"""
import json, pathlib, statistics as st

R = pathlib.Path(__file__).resolve().parents[1] / "results"
runs = [json.loads(l) for l in (R / "e5-final.jsonl").read_text().splitlines() if l.strip()]
live = [r for r in runs if not r.get("void")]
logs = {f: [json.loads(l) for l in (R / f).read_text().splitlines() if l.strip()]
        for f in ("usage.jsonl", "usage-cc.jsonl", "usage-rerun.jsonl")}

def find_block(model, total):
    hits = []
    for f, rows in logs.items():
        for i, row in enumerate(rows):
            if row["model"] != model: continue
            s = 0
            for j in range(i, len(rows)):
                if rows[j]["model"] != model: break
                s += rows[j]["prompt_tokens"]
                if s == total: hits.append((f, i, j - i + 1)); break
                if s > total: break
    return hits

import re
out = []
for r in live:
    key = dict(scaffolding=r["scaffolding"], model=r["model"], arm=r["arm"],
               total_input=r["total_input_tokens"], completed=r["completion_pct"] == 100,
               tool_calls=r.get("tool_calls"))
    noted = [m for m in (re.search(r"proxy log \((\d+) requests\)", n)
                         for n in (r.get("notes") or [])) if m]
    blocks = None if r["model"] == "sonnet-5" else find_block(r["model"], r["total_input_tokens"])
    matched = ({x[2] for x in blocks} if blocks else set())
    if noted:
        n = int(noted[0].group(1))
        # where both sources exist they must agree -- capture-time count vs sum-match
        if len(matched) == 1 and matched != {n}:
            raise SystemExit(f"cross-check failed: {key} notes={n} sum-match={matched}")
        key.update(n_requests=n, source="notes (capture-time proxy count)")
    elif len(matched) == 1:
        key.update(n_requests=matched.pop(), source="proxy sum-match")
    elif r["model"] == "sonnet-5":
        key.update(n_requests=None, source="self-reported; no proxy rows")
    else:
        key.update(n_requests=None, source="no-block-match")
    out.append(key)

# validate the pi estimator on the matched pi runs, then apply to the misses
pi_ok = [r for r in out if r["scaffolding"] == "pi" and r["n_requests"]]
for r in pi_ok:
    assert r["n_requests"] == r["tool_calls"] + 1, (r, "pi rule broken")
for r in out:
    if r["scaffolding"] == "pi" and r["n_requests"] is None:
        r.update(n_requests=r["tool_calls"] + 1, source="estimated: tool_calls+1 (validated on matched pi runs)")

(R / "requests-per-run.jsonl").write_text("\n".join(json.dumps(r) for r in out) + "\n")
att = [r for r in out if r["n_requests"]]
print(f"attributed {len(att)}/{len(out)} live runs "
      f"({sum(1 for r in att if r['source'].startswith('estimated'))} estimated, "
      f"{len(out)-len(att)} excluded)")

# ---- Table A: paired decomposition (both arms completed, both attributed) ----
by = {}
for r in att:
    if r["completed"]: by.setdefault((r["scaffolding"], r["model"]), {})[r["arm"]] = r
print("\nPAIRED DECOMPOSITION  total = xrequests * xtokens/request")
rows = []
for (s, m), arms in sorted(by.items()):
    if "cli" not in arms or "mcp" not in arms: continue
    c, k = arms["cli"], arms["mcp"]
    total = k["total_input"] / c["total_input"]
    xreq = k["n_requests"] / c["n_requests"]
    xtpr = (k["total_input"] / k["n_requests"]) / (c["total_input"] / c["n_requests"])
    rows.append((s, m, total, xreq, xtpr))
for s, m, t, xr, xt in sorted(rows, key=lambda x: x[2]):
    print(f"  {s:<12} {m:<14} total x{t:5.2f}  = req x{xr:4.2f} * tok/req x{xt:4.2f}")
print(f"  pairs: {len(rows)}  total span {min(r[2] for r in rows):.2f}-{max(r[2] for r in rows):.2f}"
      f"  tok/req span {min(r[4] for r in rows):.2f}-{max(r[4] for r in rows):.2f}"
      f"  req span {min(r[3] for r in rows):.2f}-{max(r[3] for r in rows):.2f}")

# ---- Table B: CLI arm by scaffolding ----
print("\nCLI ARM BY SCAFFOLDING  (completed runs)")
cli = {}
for r in att:
    if r["arm"] == "cli" and r["completed"]: cli.setdefault(r["scaffolding"], []).append(r)
base = st.median(x["total_input"] / x["n_requests"] for x in cli["pi"])
for s in sorted(cli, key=lambda s: st.median(x["total_input"] / x["n_requests"] for x in cli[s])):
    req = st.median(x["n_requests"] for x in cli[s])
    tpr = st.median(x["total_input"] / x["n_requests"] for x in cli[s])
    print(f"  {s:<12} n={len(cli[s])}  med requests {req:4.0f}  med tok/req {tpr:8,.0f}  vs pi x{tpr/base:4.1f}")
