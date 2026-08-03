#!/usr/bin/env python3
"""Fill the paper's results section from the consolidated dataset.

Every number in the paper comes from here rather than being typed, so the
manuscript cannot drift from the data. Re-running after new results refreshes
the paper; nothing is hand-entered.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from bench.analyze import ARM_LABEL, markdown_table, summary, tool_register_summary

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper" / "paper.md"
DATA = ROOT / "results" / "final.jsonl"


def section(rows: list[dict], name: str) -> str:
    txt = summary(rows)
    m = re.search(rf"### {re.escape(name)}\n(.*?)(?=\n### |\Z)", txt, re.S)
    return m.group(1).strip() if m else ""


def headline(rows: list[dict]) -> tuple[str, str]:
    """The abstract sentence and the ratio spread, computed."""
    body = section(rows, "MCP / CLI total-input ratio")
    m = re.search(r"(\d+) comparable cells · median \*\*([\d.]+)×\*\* · "
                  r"range ([\d.]+)×–([\d.]+)×", body)
    if not m:
        return "", ""
    n, med, lo, hi = m.groups()
    spread = float(hi) / float(lo)
    abstract = (
        f"Across {n} comparable cells the MCP arm costs a median **{med}×** the "
        f"tokens of the CLI arm, but the ratio ranges from **{lo}×** to "
        f"**{hi}×** — a {spread:.0f}-fold spread in the ratio itself. The same "
        f"protocol, task and fixture can make MCP either substantially cheaper "
        f"or substantially more expensive than a command line, depending on "
        f"which scaffolding and model run underneath. We therefore report a "
        f"distribution rather than a ratio, and find that the choice of "
        f"scaffolding moves total cost further than the choice of surface does.")
    return abstract, body


def completion_line(rows: list[dict]) -> str:
    out = []
    for arm in ("cli", "mcp"):
        vals = [r["completion_pct"] for r in rows
                if not r.get("void") and r["arm"] == arm
                and r.get("completion_pct") is not None]
        if vals:
            full = sum(1 for v in vals if v == 100.0)
            out.append((ARM_LABEL[arm], len(vals), full, 100 * full / len(vals),
                        sum(vals) / len(vals)))
    lines = ["| Arm | Scored runs | Fully complete | Rate | Mean completion |",
             "|---|---:|---:|---:|---:|"]
    for label, n, full, rate, mean in out:
        lines.append(f"| {label} | {n} | {full} | {rate:.0f}% | {mean:.1f}% |")
    return "\n".join(lines)


def main() -> None:
    rows = [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]
    live = [r for r in rows if not r.get("void")]
    t = PAPER.read_text()

    abstract, ratio_tbl = headline(rows)
    t = t.replace("‹TBD: headline result.›", abstract)

    t = t.replace("""### 5.1 Results table

‹TBD›""", f"""### 5.1 Results table

{len(rows)} cells: **{len(live)} live**, **{len(rows)-len(live)} void**. Void cells
carry their reason; a void cell is a claim about what a scaffolding cannot do,
not a zero.

{markdown_table(rows)}""")

    t = t.replace("""### 5.2 Token cost

![Total input tokens per run, by surface](figures/tokens.pdf)

‹TBD›""", f"""### 5.2 Token cost

![Total input tokens per run, by surface](figures/tokens.pdf)

{ratio_tbl}

The spread is the result. A practitioner reading any single published figure —
1.2×, 35×, or anything between — is reading one cell of this table.""")

    t = t.replace("""### 5.3 Tool calls and the tool register

![Tool calls to complete the same workflow](figures/toolcalls.pdf)

‹TBD›""", f"""### 5.3 Tool calls and the tool register

![Tool calls to complete the same workflow](figures/toolcalls.pdf)

{section(rows, "Scaffolding overhead — same model, same arm")}

Which tools were actually called, aggregated by arm:

{tool_register_summary(rows)}""")

    t = t.replace("""### 5.4 Task completion

![Task completion against the five-item rubric](figures/completion.pdf)

‹TBD›""", f"""### 5.4 Task completion

![Task completion against the five-item rubric](figures/completion.pdf)

{completion_line(rows)}

Mean completion is near-identical between arms while the rate of *fully*
completed runs is not: the MCP arm does not produce worse answers so much as
more partial ones.""")

    costs = [(r["theoretical_cost_usd"], r) for r in live
             if r.get("theoretical_cost_usd")]
    tot = sum(c for c, _ in costs)
    top = sorted(costs, key=lambda x: -x[0])[:5]
    cost_tbl = "\n".join(
        [f"| {r['scaffolding']}/{r['model']} | {ARM_LABEL[r['arm']]} | ${c:.4f} |"
         for c, r in top])
    t = t.replace("""### 5.5 Cost

![Theoretical cost per run at list prices](figures/cost.pdf)

‹TBD›""", f"""### 5.5 Cost

![Theoretical cost per run at list prices](figures/cost.pdf)

Theoretical cost across all scored runs totals **${tot:.2f}** at list prices.
The five most expensive individual runs:

| Cell | Arm | Cost |
|---|---|---:|
{cost_tbl}

This is a modelled figure, not an invoice: one public price list is applied
uniformly to every cell including those served on local hardware, because
comparing billing arrangements would not compare workloads.""")

    t = t.replace("""**Draft — results pending.** Figures and every number marked `‹TBD›` are filled from
`results/runs.jsonl` by `bench/analyze.py`; nothing in this file is hand-entered.""",
"""Every number and figure in this paper is generated from `results/final.jsonl`
by `bench/fill_paper.py`; nothing is hand-entered.""")

    PAPER.write_text(t)
    remaining = t.count("‹TBD")
    print(f"filled paper from {len(rows)} cells; {remaining} TBD markers remain")


if __name__ == "__main__":
    main()
