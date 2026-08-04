"""Spend ceiling enforced in the harness.

litellm's max_budget needs a database backend; without one it fails every
request with "400 No connected db", which silently killed three cells. The
ceiling therefore lives here, computed from the proxy's usage log — the same
records that make sub-agent spend visible — and needs no external service.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from bench.costs import PRICES, theoretical_cost

ROOT = Path(__file__).resolve().parent.parent
# The ceiling applies to the CURRENT experiment, whose requests land in the log
# named by E1_USAGE_LOG. Charging a new experiment for a previous one's spend
# blocks work that is within its own budget — which is exactly what happened when
# the re-run refused to start.
USAGE = Path(os.environ.get("E1_USAGE_LOG", str(ROOT / "results" / "usage.jsonl")))
LIFETIME = sorted((ROOT / "results").glob("usage*.jsonl"))
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


def lifetime_usd() -> float:
    """Spend across every experiment, for reporting — never for gating."""
    return round(sum(spent_usd(p) for p in LIFETIME), 4)


def check(budget: float) -> None:
    """Raise before starting a cell that would breach this experiment's ceiling."""
    used = spent_usd()
    if used >= budget:
        raise SystemExit(f"budget exhausted for this experiment: ${used:.2f} of "
                         f"${budget:.2f} in {USAGE.name} — raise --budget to continue")


if __name__ == "__main__":
    print(f"this experiment ({USAGE.name}): ${spent_usd():.4f}")
    print(f"lifetime across all experiments: ${lifetime_usd():.4f}")
