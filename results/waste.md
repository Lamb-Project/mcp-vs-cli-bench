============================================================================
SCAFFOLDING — Experiment 1 (re-run)
============================================================================

  scaffolding   runs  median tok  full done  MCP support
  pi               5       6,540       5/5           no   ×1
  codex           10      42,074      10/10          yes   ×6
  claude-code      4     126,484       4/4          yes   ×19
  qwen-code       10     180,594       5/10          yes   ×28

============================================================================
WASTED TOOL CALLS — Experiment 1 (re-run)
============================================================================

  arm    runs  calls  wasted  % wasted
  CLI      17    120      18     15.0%
  MCP      11    133      49     36.8%

  scaffolding   runs  calls  navel  redun  repeat  % wasted
  qwen-code        9     96      5      1      34     41.7%
  codex           10    100      4      0      14     18.0%
  claude-code      4     31      2      2       1     16.1%
  pi               5     26      0      0       4     15.4%

  worst offenders:
    codex/qwen3.6:27b/mcp: 10 wasted of 20 calls, done=100.0%
        shell:gh×14, mcp__list_mcp_resource_templates×2
    qwen-code/qwen3.6:27b/cli: 9 wasted of 15 calls, done=100.0%
        web_fetch×15
    qwen-code/gpt-5.6-luna/mcp: 8 wasted of 16 calls, done=100.0%
        mcp__github__get_file_contents×12, tool_search×2
    qwen-code/qwen3.6:27b/mcp: 8 wasted of 15 calls, done=80.0%
        mcp__github__get_file_contents×12, mcp__github__get_me×1, mcp__github__search_repositories×1
    qwen-code/gpt-5.6-terra/mcp: 7 wasted of 15 calls, done=80.0%
        mcp__github__get_file_contents×12, tool_search×1
    qwen-code/glm-5.2/mcp: 7 wasted of 15 calls, done=80.0%
        mcp__github__get_file_contents×12, tool_search×1

============================================================================
SCAFFOLDING — Experiment 3 (corrected)
============================================================================

  scaffolding   runs  median tok  full done  MCP support
  pi               3      13,588       3/3           no   ×1
  codex            8     141,918       6/8          yes   ×10
  qwen-code        8     258,405       7/8          yes   ×19
  claude-code      2     450,360       1/2          yes   ×33

============================================================================
WASTED TOOL CALLS — Experiment 3 (corrected)
============================================================================

  arm    runs  calls  wasted  % wasted
  CLI      12    142      18     12.7%
  MCP       9    202      70     34.7%

  scaffolding   runs  calls  navel  redun  repeat  % wasted
  claude-code      2     24      3      0       7     41.7%
  codex            8    214     14      0      48     29.0%
  pi               3     26      0      0       5     19.2%
  qwen-code        8     80      5      0       6     13.8%

  worst offenders:
    codex/qwen3.6:27b/mcp: 52 wasted of 108 calls, done=100.0%
        mcp__read_mcp_resource×28, shell:TOKEN=×14, shell:ls×12, shell:rg×12
    claude-code/sonnet-5/cli: 7 wasted of 14 calls, done=100.0%
        Bash×13
    codex/glm-5.2/mcp: 6 wasted of 30 calls, done=100.0%
        shell:curl×8, mcp__list_mcp_resources×2, mcp__list_mcp_resource_templates×2
    pi/gpt-5.6-luna/cli: 4 wasted of 13 calls, done=100.0%
        bash×10
    claude-code/sonnet-5/mcp: 3 wasted of 10 calls, done=25.0%
        mcp__github__get_me×2, ToolSearch×1
    qwen-code/glm-5.2/mcp: 3 wasted of 8 calls, done=50.0%
        tool_search×3

