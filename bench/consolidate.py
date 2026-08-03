#!/usr/bin/env python3
"""Merge run files into the single dataset the paper reports.

Several cells were collected more than once — some because a scaffolding's
config leaked between arms and had to be re-run under isolation, some because a
parameter incompatibility was fixed by putting the proxy in the path. Later runs
supersede earlier ones for the same cell, and the reason is recorded so the
provenance of every row is visible rather than implied by file order.

Precedence is explicit rather than "last file wins", because a re-run that
errored should not silently replace a good earlier result.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# lowest precedence first; later files supersede earlier ones for the same cell
SOURCES = [
    ("runs.jsonl", "initial matrix"),
    ("runs-codex-clean.jsonl", "codex re-run under per-run CODEX_HOME isolation"),
    ("runs-qwen-clean.jsonl", "qwen-code re-run through the proxy (max_tokens fix)"),
    ("runs-codex5x-clean.jsonl", "codex gpt-5.x re-run under isolation"),
    ("runs-pi-fix.jsonl", "pi hosted cells re-run after the proxy key collision"),
]

OUT = RESULTS / "final.jsonl"


def key(r: dict) -> tuple[str, str, str]:
    return (r["scaffolding"], r["model"], r["arm"])


def usable(r: dict) -> bool:
    """A row worth keeping: void cells are meaningful; errored ones are not."""
    if r.get("void"):
        return True
    return not r.get("error") and r.get("completion_pct") is not None


def main() -> None:
    merged: dict[tuple[str, str, str], dict] = {}
    for fname, why in SOURCES:
        p = RESULTS / fname
        if not p.exists():
            continue
        n = 0
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            k = key(r)
            prev = merged.get(k)
            # a broken re-run must not displace a good earlier result
            if prev is not None and usable(prev) and not usable(r):
                continue
            if prev is not None:
                r.setdefault("notes", []).append(f"supersedes earlier run: {why}")
            merged[k] = r
            n += 1
        print(f"  {fname}: {n} rows ({why})")

    rows = [merged[k] for k in sorted(merged)]
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    live = [r for r in rows if not r.get("void")]
    ok = [r for r in live if r.get("completion_pct") is not None]
    print(f"\n{len(rows)} cells -> {OUT}")
    print(f"  live: {len(live)}   void: {len(rows)-len(live)}   scored: {len(ok)}")
    incomplete = [r for r in rows if r.get("totals_incomplete")]
    if incomplete:
        names = ["/".join((r["scaffolding"], r["model"], r["arm"]))
                 for r in incomplete]
        print("  flagged totals_incomplete (sub-agent tokens off-thread): "
              + ", ".join(names))


if __name__ == "__main__":
    main()
