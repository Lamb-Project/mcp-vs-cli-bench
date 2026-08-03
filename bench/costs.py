"""Theoretical cost model, using OpenRouter's advertised per-token prices.

Why theoretical rather than billed: half the models here run on local hardware
where the marginal cost is electricity, and the rest run through different
billing paths (a subscription, a pay-as-you-go key). Billed cost would therefore
compare accounting arrangements rather than workloads.

Applying one public price list uniformly to every cell — local models included —
makes the columns comparable and makes the number reproducible by anyone, since
the price list is public and dated. Real spend is recorded separately and never
mixed into this figure.

Prices are $ per million tokens, captured on the date below. They move; re-fetch
with `python -m bench.costs --refresh` and re-report the date alongside results.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from dataclasses import dataclass

PRICES_CAPTURED = "2026-08-03"

# model key -> (input $/M, output $/M, openrouter id)
PRICES: dict[str, tuple[float, float, str]] = {
    # gpt-5.6 (sol/luna/terra) is OpenRouter-only and that key returns 401
    # "User not found"; these are the hosted OpenAI models the repo key reaches.
    "gpt-5.2":        (1.75, 14.00, "openai/gpt-5.2"),
    "gpt-5.1":        (1.25, 10.00, "openai/gpt-5.1"),
    "gpt-5-mini":     (0.25,  2.00, "openai/gpt-5-mini"),
    "sonnet-5":       (2.00, 10.00, "anthropic/claude-sonnet-5"),
    "opus-5":         (5.00, 25.00, "anthropic/claude-opus-5"),
    "fable-5":       (10.00, 50.00, "anthropic/claude-fable-5"),
    "glm-5.2":        (1.19,  3.74, "z-ai/glm-5.2"),
    "qwen3.6:27b":    (0.30,  2.00, "qwen/qwen3.6-27b"),
    # qwen3.5:122b is served locally; OpenRouter lists the -a10b variant, which
    # is the closest public price for the same weights class.
    "qwen3.5:122b":   (0.30,  2.00, "qwen/qwen3.5-122b-a10b"),
}


@dataclass(frozen=True)
class Cost:
    input_usd: float
    output_usd: float

    @property
    def total_usd(self) -> float:
        return round(self.input_usd + self.output_usd, 6)


def theoretical_cost(model: str, input_tokens: int, output_tokens: int,
                     cached_tokens: int = 0, cache_discount: float = 0.0) -> Cost:
    """Cost of one run at list price.

    `cache_discount` defaults to 0: cached input is billed as input. Providers
    discount cached reads at different rates (and local inference has no billing
    concept at all), so assuming a discount would bake one vendor's policy into
    a cross-vendor comparison. The cache-hit percentage is reported as its own
    dimension instead, where the reader can apply whatever discount they like.
    """
    if model not in PRICES:
        raise KeyError(f"no price for {model!r}; add it to bench.costs.PRICES")
    in_rate, out_rate, _ = PRICES[model]
    billable_in = input_tokens - int(cached_tokens * cache_discount)
    return Cost(
        input_usd=round(billable_in / 1e6 * in_rate, 6),
        output_usd=round(output_tokens / 1e6 * out_rate, 6),
    )


def refresh() -> None:
    """Re-fetch live prices and print a PRICES block to paste back in."""
    req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                 headers={"User-Agent": "mcp-vs-cli-bench"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    by_id = {m["id"]: m for m in data["data"]}
    for key, (_, _, rid) in PRICES.items():
        m = by_id.get(rid)
        if not m:
            print(f"  # {key}: {rid} NOT FOUND upstream", file=sys.stderr)
            continue
        p = m["pricing"]
        print(f'    "{key}": ({float(p["prompt"])*1e6:.2f}, '
              f'{float(p["completion"])*1e6:.2f}, "{rid}"),')


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    else:
        print(f"prices captured {PRICES_CAPTURED}")
        for k, (i, o, rid) in PRICES.items():
            print(f"  {k:<16} in ${i:>6.2f}/M  out ${o:>6.2f}/M   {rid}")
