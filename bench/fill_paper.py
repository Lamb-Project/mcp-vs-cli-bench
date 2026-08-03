#!/usr/bin/env python3
"""Regenerate the paper's results sections from the consolidated dataset.

Every number in the paper is produced here rather than typed, so the manuscript
cannot drift from the data.

Sections are replaced **by heading**, not by consuming a one-shot placeholder.
Placeholder-filling is not idempotent: once the marker is gone a re-run silently
does nothing, which is exactly how a stale completion table survived a re-fill
after three more cells landed. Replacing whole sections means the paper always
reflects the current dataset, however many times this runs.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from bench.analyze import ARM_LABEL, markdown_table, summary, tool_register_summary

ROOT = Path(__file__).resolve().parent.parent
# The manuscript is drafted outside this repository; override with BENCH_PAPER.
# This repo publishes the harness and the data, not the write-up.
PAPER = Path(os.environ.get("BENCH_PAPER", str(
    Path.home() / "Documents/ludo-claude/ludo-writting-workshop/writting-projects"
                  "/papers/2026/mcp-vs-cli-benchmark/paper-draft-v1.md")))
DATA = ROOT / "results" / "final.jsonl"


def part(rows: list[dict], name: str) -> str:
    txt = summary(rows)
    m = re.search(rf"### {re.escape(name)}\n(.*?)(?=\n### |\Z)", txt, re.S)
    return m.group(1).strip() if m else ""


def replace_section(text: str, heading: str, body: str) -> str:
    """Swap the body of a `### heading` section, keeping the heading itself."""
    # stop at the next heading of ANY level: "^## " also matches "^### ", so a
    # single-# lookahead let section 5.1 swallow 5.2 through 5.5.
    pat = re.compile(rf"(^### {re.escape(heading)}\n)(.*?)(?=^#{{2,4}} |\Z)",
                     re.S | re.M)
    if not pat.search(text):
        raise KeyError(f"section not found: {heading}")
    return pat.sub(lambda m: m.group(1) + "\n" + body.strip() + "\n\n", text)


def abstract_sentence(rows: list[dict]) -> tuple[str, str]:
    body = part(rows, "MCP / CLI total-input ratio")
    m = re.search(r"(\d+) comparable cells · median \*\*([\d.]+)×\*\* · "
                  r"range ([\d.]+)×–([\d.]+)×", body)
    if not m:
        return "", body
    n, med, lo, hi = m.groups()
    spread = float(hi) / float(lo)
    return (f"Across {n} comparable cells the MCP arm costs a median **{med}×** "
            f"the tokens of the CLI arm, but the ratio ranges from **{lo}×** to "
            f"**{hi}×** — a {spread:.0f}-fold spread in the ratio itself. The "
            f"same protocol, task and fixture can make MCP either substantially "
            f"cheaper or substantially more expensive than a command line, "
            f"depending on which scaffolding and model run underneath. We "
            f"therefore report a distribution rather than a ratio, and find that "
            f"the choice of scaffolding moves total cost further than the choice "
            f"of surface does."), body


def completion_table(rows: list[dict]) -> str:
    lines = ["| Arm | Scored runs | Fully complete | Rate | Mean completion |",
             "|---|---:|---:|---:|---:|"]
    for arm in ("cli", "mcp"):
        vals = [r["completion_pct"] for r in rows
                if not r.get("void") and r["arm"] == arm
                and r.get("completion_pct") is not None]
        if not vals:
            continue
        full = sum(1 for v in vals if v == 100.0)
        lines.append(f"| {ARM_LABEL[arm]} | {len(vals)} | {full} | "
                     f"{100*full/len(vals):.0f}% | {sum(vals)/len(vals):.1f}% |")
    return "\n".join(lines)


def cost_table(live: list[dict]) -> tuple[str, float]:
    costs = [(r["theoretical_cost_usd"], r) for r in live
             if r.get("theoretical_cost_usd")]
    tot = sum(c for c, _ in costs)
    top = sorted(costs, key=lambda x: -x[0])[:5]
    tbl = "\n".join(f"| {r['scaffolding']}/{r['model']} | {ARM_LABEL[r['arm']]} "
                    f"| ${c:.4f} |" for c, r in top)
    return tbl, tot


def main() -> None:
    rows = [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]
    live = [r for r in rows if not r.get("void")]
    t = PAPER.read_text()

    abstract, ratio_tbl = abstract_sentence(rows)
    t = re.sub(r"(?<=\n)Across \d+ comparable cells the MCP arm costs.*?"
               r"choice of surface does\.", abstract, t, flags=re.S)
    t = t.replace("‹TBD: headline result.›", abstract)

    t = replace_section(t, "5.1 Results table", f"""{len(rows)} cells: **{len(live)} live**, **{len(rows)-len(live)} void**. Void cells
carry their reason; a void cell is a claim about what a scaffolding cannot do,
not a zero.

{markdown_table(rows)}""")

    t = replace_section(t, "5.2 Token cost", f"""![Total input tokens per run, by surface](figures/tokens.pdf)

{ratio_tbl}

The spread is the result. A practitioner reading any single published figure —
1.2×, 35×, or anything between — is reading one cell of this table.""")

    t = replace_section(t, "5.3 Tool calls and the tool register",
                        f"""![Tool calls to complete the same workflow](figures/toolcalls.pdf)

{part(rows, "Scaffolding overhead — same model, same arm")}

Which tools were actually called, aggregated by arm:

{tool_register_summary(rows)}""")

    t = replace_section(t, "5.4 Task completion",
                        f"""![Task completion against the five-item rubric](figures/completion.pdf)

{completion_table(rows)}

Mean completion is near-identical between arms while the rate of *fully*
completed runs is not: the MCP arm does not produce worse answers so much as
more partial ones.""")

    tbl, tot = cost_table(live)
    t = replace_section(t, "5.5 Cost", f"""![Theoretical cost per run at list prices](figures/cost.pdf)

Theoretical cost across all scored runs totals **${tot:.2f}** at list prices.
The five most expensive individual runs:

| Cell | Arm | Cost |
|---|---|---:|
{tbl}

This is a modelled figure, not an invoice: one public price list is applied
uniformly to every cell including those served on local hardware, because
comparing billing arrangements would not compare workloads.""")

    t = t.replace("""**Draft — results pending.** Figures and every number marked `‹TBD›` are filled from
`results/runs.jsonl` by `bench/analyze.py`; nothing in this file is hand-entered.""",
"""Every number and figure in this paper is generated from `results/final.jsonl`
by `bench/fill_paper.py`; nothing is hand-entered.""")

    PAPER.write_text(t)
    print(f"regenerated results sections from {len(rows)} cells "
          f"({len(live)} live); {t.count('‹TBD')} placeholders remain")


if __name__ == "__main__":
    main()
