# mcp-vs-cli-bench

An open benchmark comparing **MCP tool use** against **CLI tool use** across agent
scaffoldings and models.

Connecting a tool catalogue over the Model Context Protocol places every tool's
schema in the model's context. Exposing the same capability through a
command-line tool places a command string there instead. The difference is
widely asserted and rarely measured across more than one setup. This benchmark
measures it on a fixed task, across four scaffoldings and nine models, and
publishes the harness so the numbers can be checked.

## What is measured

One workflow, five independently checkable sub-answers, run twice per
scaffolding/model pair — once with a GitHub MCP server attached, once with the
scaffolding's native shell and the `gh` CLI.

Per run:

| Dimension | Notes |
|---|---|
| Initial tokens | first-request prompt size — the surface's fixed cost |
| Total input / output tokens | whole workflow |
| Cached tokens, cache-hit % | reported separately; never folded into cost |
| Tool calls | count **and a register of which tools were called** |
| Tool success ratio | successful calls / total calls |
| Task completion % | scored against the rubric, not pass/fail |
| Theoretical cost | OpenRouter list prices applied uniformly to every cell |
| Wall time | recorded, but **not comparable** across local and hosted inference |

## Scaffoldings and models

| Scaffolding | Models | MCP arm | CLI arm |
|---|---|:--:|:--:|
| Claude Code | sonnet-5, opus-5, fable-5 | ✅ | ✅ |
| Codex | gpt-5.6 sol/luna/terra, glm-5.2, qwen3.5:122b, qwen3.6:27b | ✅ | ✅ |
| qwen-code | same six | ✅ | ✅ |
| pi | same six | ⛔ **void** | ✅ |

**pi ships no MCP client** — no flag, no configuration, nothing in its help
output. Its MCP cells are reported void rather than as zeros, because "cannot"
and "costs nothing" are different claims.

**Claude Code reaches only Anthropic models**; it has no custom-endpoint path.

Every scaffolding is run in its **default configuration** — no tool pruning, no
registry trimming — with thinking disabled or set to its lowest setting. The
question is what a practitioner gets, not what a tuned harness can be made to do.

## Why theoretical cost

Half these models run on local hardware where marginal cost is electricity, and
the rest bill through different arrangements. Comparing invoices would compare
accounting, not workloads. One public, dated price list applied uniformly makes
the column reproducible; real spend is reported separately and never mixed in.

Cached input is billed as input (no discount assumed) because providers discount
it differently and local inference has no billing concept at all. Cache-hit rate
is its own column, so any reader can apply their own discount.

## Reproducing

Requirements, and each one changes the numbers if skipped:

- **llama-server with `--reasoning off`** for GLM. Its thinking mode can run away
  without terminating; the published figures assume it is off.
- **The pinned fixture** `Lamb-Project/aawd-e1-fixture` at tag `fixture-v1`, so
  ground truth cannot drift.
- **`fastapi==0.136.3`** if using the LiteLLM proxy — litellm 1.95.0 declares a
  range that includes versions which break its own import.
- **KV cache cleared between local runs.** llama-server persists cache to disk,
  so whichever arm runs second otherwise starts warm and looks cheap.

```bash
uv venv && uv pip install -e .
python -m bench.runner --estimate-only     # spend estimate first
python -m bench.runner --budget 5.00
python -m bench.analyze                    # tables + figures
```

## Layout

```
bench/       task definition + rubric, cost model, adapters, runner, analysis
setup/       LiteLLM proxy config and per-request usage callback
results/     raw JSONL, one record per run
paper/       the write-up, sources and figures
```

## Status

Pre-release. The matrix has been costed and the harness verified against every
scaffolding's telemetry format; results are being collected.

## Licence

MIT.
