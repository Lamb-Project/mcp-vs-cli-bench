# mcp-vs-cli-bench

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21851992.svg)](https://doi.org/10.5281/zenodo.21851992)

An open benchmark comparing **MCP tool use** against **CLI tool use** across agent
scaffoldings and models.

Connecting a tool catalogue over the Model Context Protocol places every tool's
schema in the model's context. Exposing the same capability through a
command-line tool places a command string there instead. The difference is
widely asserted and rarely measured across more than one setup. This benchmark
measures it on a fixed task, across seven scaffoldings and five models, and
publishes the harness so the numbers can be checked.

## What is measured

One workflow — six operations against a private GitHub repository — run twice
per scaffolding/model pair: once with the official GitHub MCP server attached,
once with the scaffolding's native shell and the `gh` CLI. Completion is scored
over four independently verifiable conditions by reading repository state back
through the API, never by trusting the agent's own report.

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

| Scaffolding | MCP arm | CLI arm |
|---|:--:|:--:|
| Claude Code | ✅ | ✅ |
| OpenAI Codex | ✅ | ✅ |
| qwen-code | ✅ | ✅ |
| Hermes | ✅ | ✅ |
| opencode | ✅ | ✅ |
| pi | ⛔ **void** | ✅ |
| Tau | ⛔ **void** | ✅ |

Models: `gpt-5.6-luna`, `gpt-5.6-terra` (hosted), `glm-5.2`, `qwen3.6:27b`
(served locally), and `sonnet-5` (Claude Code on its subscription credential).

**pi and Tau ship no MCP client** — their MCP cells are reported void rather
than as zeros, because "cannot" and "costs nothing" are different claims.

**Claude Code is measured at the proxy like everything else.** Pointing
`ANTHROPIC_BASE_URL` at the LiteLLM proxy routes it to any model speaking the
Anthropic message format; only the two cells run on a subscription credential
bypass the proxy and self-report, and on the proxied runs the two accountings
agree to the token.

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
- **The private fixture** `Lamb-Project/aawd-e2-fixture`, reset by
  `bench.seed_e2` before every run so one run's leftovers cannot satisfy the
  next run's checks.
- **`fastapi==0.136.3`** if using the LiteLLM proxy — litellm 1.95.0 declares a
  range that includes versions which break its own import.
- **KV cache cleared between local runs.** llama-server persists cache to disk,
  so whichever arm runs second otherwise starts warm and looks cheap.

```bash
./setup/install.sh                  # scaffoldings, MCP server, proxy; checks preconditions
python setup/configure_pi.py        # register pi's providers
.venv-litellm/bin/litellm --config setup/litellm_config.yaml --port 4000 &

python -m bench.runner --estimate-only     # spend estimate; refuses to exceed budget
python -m bench.runner --budget 5.00
python -m bench.consolidate_v10            # build results/e5-final.jsonl from the run files
BENCH_DATASET=e5-final.jsonl python -m bench.analysis_v6   # the paper's tables
BENCH_DATASET=e5-final.jsonl python -m bench.verify_paper  # recompute every published number
```

`install.sh` refuses to proceed if a precondition is wrong rather than producing
numbers that will not reproduce.

**Everything routes through the LiteLLM proxy**, for two reasons beyond
telemetry. A scaffolding that delegates to sub-agents bills those children to
separate threads whose tokens never reach the parent's usage record, and the
proxy sees those requests. And `max_budget` caps spend upstream of the harness,
so a looping agent cannot overrun the ceiling. The proxy adds no tokens, so
routing through it does not change what is measured. It also pins
`reasoning_effort` on hosted models, which is the only layer where "thinking
off" cannot be forgotten per-scaffolding.

## Layout

```
bench/       task definition + rubric, cost model, adapters, runner, analysis
setup/       LiteLLM proxy config and per-request usage callback
results/     raw JSONL per run, plus the consolidated dataset
```

## The write-up

This repository publishes the **benchmark and its data** — the part that has to be
re-runnable and checkable. The manuscript is drafted separately and released on
submission. `bench/fill_paper.py` still generates its results sections from
`results/final.jsonl`, taking the manuscript path from `BENCH_PAPER`, so the
figures and tables remain reproducible from the published data.

## Status

Results collected. The main matrix is 54 cells across seven agent scaffoldings
and five models, with the locally-served configurations repeated three times so
that run-to-run variation is measured rather than assumed. `bench/verify_paper.py`
recomputes every number in the accompanying manuscript from the dataset.

## Authors

- Marc Alier — Universitat Politècnica de Catalunya (UPC), Barcelona
- María José Casañ — Universitat Politècnica de Catalunya (UPC), Barcelona
- Francisco José García-Peñalvo — Universidad de Salamanca (USAL), Salamanca
- Juanan Pereira — Universidad del País Vasco / Euskal Herriko Unibertsitatea (UPV/EHU), Donostia-San Sebastián

Correspondence: `marc.alier@upc.edu`

## Licence

Copyright © 2026 Marc Alier, Juanan Pereira, María José Casañ and
Francisco José García-Peñalvo.

This program is free software: you can redistribute it and/or modify it under
the terms of the **GNU General Public License** as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. It is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the [LICENSE](LICENSE) file, or
<https://www.gnu.org/licenses/>, for the full terms.

Same licence and the same authorship as the [LAMB
project](https://github.com/Lamb-Project), of which this benchmark is a part.
