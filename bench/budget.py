"""Spend ceiling enforced in the harness.

litellm's max_budget needs a database backend; without one it fails every
request with "400 No connected db", which silently killed three cells. The
ceiling therefore lives here, computed from the proxy's usage log — the same
records that make sub-agent spend visible — and needs no external service.
"""
from __future__ import annotations

import json
from pathlib import Path

from bench.costs import PRICES, theoretical_cost

ROOT = Path(__file__).resolve().parent.parent
USAGE = ROOT / "results" / "usage.jsonl"
LOCAL_PREFIXES = ("glm", "qwen3")


def spent_usd(path: Path = USAGE) -> float:
    """Metered spend so far. Local inference is free and excluded."""
    if not path.exists():
        return 0.0
    total = 0.0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "error" in r:
            continue
        model = (r.get("model") or "").split("/")[-1]
        if model not in PRICES or model.startswith(LOCAL_PREFIXES):
            continue
        total += theoretical_cost(model, r.get("prompt_tokens") or 0,
                                  r.get("completion_tokens") or 0).total_usd
    return round(total, 4)


def check(budget: float) -> None:
    """Raise before starting a cell that would breach the ceiling."""
    used = spent_usd()
    if used >= budget:
        raise SystemExit(f"budget exhausted: ${used:.2f} spent of ${budget:.2f} — "
                         "raise --budget explicitly to continue")


if __name__ == "__main__":
    print(f"metered spend so far: ${spent_usd():.4f}")
