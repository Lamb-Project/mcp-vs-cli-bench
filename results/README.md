# Results

One JSON object per run, one run per line.

## Files

| File | What |
|---|---|
| `runs.jsonl` | the initial matrix plus the gpt-5.6 cells |
| `runs-codex-clean.jsonl` | codex re-run under per-run config isolation |
| `runs-qwen-clean.jsonl` | qwen-code re-run through the proxy |
| `final.jsonl` | **the dataset the paper reports** — produced by `bench.consolidate` |
| `usage.jsonl` | **per-request** usage recorded by the proxy — 342 requests |
| `runs/<cell>/` | raw `stdout.txt` and `stderr.txt` for every cell |

Later files supersede earlier ones per cell, but a re-run that errored never
displaces a good earlier result. Rows that were superseded carry a note saying
why, so provenance is visible rather than implied by file order.

The raw per-cell output is kept deliberately: it is what makes a parser fix
applicable retroactively via `bench.reparse`, without re-running anything or
disturbing the cache state the runs control for.

## `usage.jsonl` — the proxy dataset

Every request that crossed the LiteLLM proxy on its way to a model, one line
each. This is a different and in several ways better dataset than the per-run
records, and it is published because three things are only visible here.

**Per-request granularity.** Three of the four scaffoldings report a single
cumulative usage figure per run, so the shape of a session — how cost grows turn
by turn — cannot be recovered from them. The proxy sees each request separately.

**Independence from the scaffolding's own accounting.** The per-run numbers come
from whatever each tool chooses to report. These come from the wire.

**Sub-agent traffic.** When a scaffolding delegates, the child's tokens are
billed to a thread the parent never reports. Those requests still cross the
proxy.

| Field | Meaning |
|---|---|
| `tag` | which batch the request belonged to |
| `model` | model as routed |
| `n_messages` | conversation length at the time of the request |
| `n_tools` | tool schemas sent with the request — the registry, measured per call |
| `prompt_tokens`, `completion_tokens`, `total_tokens` | as returned by the provider |
| `cached_tokens` | served from the prefix cache; `null` where a provider does not report it |
| `prefilled` | `prompt_tokens - cached_tokens` — what actually had to be processed |
| `latency_s` | request duration; **not comparable** across local and hosted inference |

`n_tools` alongside `prompt_tokens` is what makes the registry cost measurable
per request rather than inferred from a difference between runs.

## Record fields

| Field | Meaning |
|---|---|
| `scaffolding`, `model`, `arm` | the cell; `arm` is `cli` or `mcp` |
| `void`, `void_reason` | the cell cannot exist — e.g. the scaffolding ships no MCP client |
| `error` | the cell could exist but the run failed |
| `initial_tokens` | first-request prompt size — the surface's fixed cost |
| `total_input_tokens`, `total_output_tokens` | whole workflow |
| `cached_tokens`, `cache_hit_pct` | **`null` means not reported, not zero** |
| `tool_calls`, `tool_register` | how many, and which tools by name |
| `tool_failures`, `tool_success_ratio` | |
| `completion_pct`, `rubric` | percentage of the five-item rubric, and per-item results |
| `mcp_attached`, `mcp_tools_used` | server present, and whether the agent used it |
| `delegated`, `totals_incomplete` | sub-agents spawned; totals known to be short |
| `theoretical_cost_usd` | list price applied uniformly; not billed cost |
| `wall_s` | recorded, **not comparable** across local and hosted inference |
| `answer`, `notes` | final answer, and provenance notes |

## Three distinctions the schema keeps apart

**`null` versus `0`.** A scaffolding that does not report cached tokens gets
`null`; one that reports none gets `0`. Collapsing these would make Ollama-served
cells look like cache failures rather than unreported measurements.

**Void versus failed.** `void` means the cell cannot exist — pi has no MCP client,
so there is nothing to measure. `error` means it could have existed and did not
work. They support opposite conclusions and are never merged.

**`mcp_attached` versus `mcp_tools_used`.** A server can be attached and enabled
while the agent completes the task entirely through its shell. That is a result
about tool selection, not a broken cell, so it is recorded rather than voided.

**`totals_incomplete`.** When a scaffolding delegates to sub-agents, their tokens
are billed to separate threads and never appear in the parent's usage record.
Those cells are excluded from ratio comparisons. Routing through the proxy is
what recovers the missing requests, since the children's calls cross it too.
