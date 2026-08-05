==========================================================================
AUDIT — Experiment 1 (re-run, uniform routing)  (34 cells)
==========================================================================

  ⚠ cache figure absent — provider does not report it (not a zero)  (10)
      codex/qwen3.5:122b/cli
      codex/qwen3.6:27b/cli
      qwen-code/qwen3.5:122b/cli
      qwen-code/qwen3.6:27b/cli
      pi/qwen3.5:122b/cli
      pi/qwen3.6:27b/cli
      codex/qwen3.5:122b/mcp
      codex/qwen3.6:27b/mcp

  ⚠ arm mismatch (behaviour ≠ assignment)  (13)
      qwen-code/gpt-5.6-luna/cli -> web-api
      qwen-code/gpt-5.6-terra/cli -> web-api
      qwen-code/glm-5.2/cli -> mixed
      qwen-code/qwen3.5:122b/cli -> no-tools
      qwen-code/qwen3.6:27b/cli -> web-api
      claude-code/sonnet-5/mcp -> mixed
      claude-code/opus-5/mcp -> mixed
      codex/gpt-5.6-luna/mcp -> pure-cli

  ⚠ tokens/call more than 5× the median (11,538)  (1)
      qwen-code/qwen3.5:122b/cli: 66,340/call, 1 calls, done=0.0

  ⚠ ratio < 1 (failure signature unless explained)  (2)
      codex/glm-5.2: 0.82× — impure
      qwen-code/qwen3.6:27b: 0.97× — incomplete impure

  26 flagged observations in Experiment 1 (re-run, uniform routing)

==========================================================================
AUDIT — Experiment 3 (private fixture, isolated)  (26 cells)
==========================================================================

  ⚠ cache figure absent — provider does not report it (not a zero)  (4)
      codex/qwen3.6:27b/cli
      qwen-code/qwen3.6:27b/cli
      codex/qwen3.6:27b/mcp
      qwen-code/qwen3.6:27b/mcp

  ⚠ arm mismatch (behaviour ≠ assignment)  (4)
      claude-code/sonnet-5/mcp -> mixed
      codex/gpt-5.6-terra/mcp -> mixed
      codex/glm-5.2/mcp -> mixed
      codex/qwen3.6:27b/mcp -> mixed

  ⚠ call count more than 4× the median (10) — likely a loop  (1)
      codex/qwen3.6:27b/mcp: 108 calls, done=80.0

  ⚠ ratio < 1 (failure signature unless explained)  (4)
      claude-code/sonnet-5: 0.66× — incomplete impure
      qwen-code/gpt-5.6-luna: 0.65× — incomplete
      qwen-code/gpt-5.6-terra: 0.96× — incomplete
      qwen-code/glm-5.2: 0.53× — incomplete

  ⚠ ratio > 10× — check for a stalled or truncated arm  (1)
      codex/qwen3.6:27b: 29.1× — CLI 83,247 (16 calls, 80.0%) vs MCP 2,418,828 (108 calls, 80.0%)

  14 flagged observations in Experiment 3 (private fixture, isolated)

