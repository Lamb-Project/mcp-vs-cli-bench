========================================================================
Q0  Did each run use exclusively the method it was assigned?
========================================================================
  assigned CLI : mixed=2, no-tools=3, pure-cli=21, web-api=4
  assigned MCP : mixed=6, no-tools=3, pure-cli=6, pure-mcp=6, void=9

  Runs whose actual behaviour does not match their assignment:
    claude-code/fable-5/mcp -> mixed     [mcp__github__get_file_contents×3, Bash×3, ToolSearch×1]
    claude-code/opus-5/mcp -> mixed     [Bash×3, mcp__github__get_file_contents×2, ToolSearch×1]
    claude-code/sonnet-5/mcp -> mixed     [Bash×5, ToolSearch×4, mcp__github__get_file_contents×2]
    codex/glm-5.2/mcp -> pure-cli  [shell:gh×12]
    codex/gpt-5-mini/cli -> mixed     [shell:curl×12, shell:git×2]
    codex/gpt-5-mini/mcp -> no-tools  []
    codex/gpt-5.2/mcp -> pure-cli  [shell:set×2]
    codex/gpt-5.6-luna/mcp -> pure-cli  [shell:set×2]
    codex/gpt-5.6-terra/mcp -> pure-cli  [shell:git×2, shell:target_dir=$(mktemp×2]
    codex/qwen3.5:122b/mcp -> pure-cli  [shell:git×6, shell:pwd×2, shell:ls×2]
    codex/qwen3.6:27b/mcp -> mixed     [shell:curl×8, mcp__list_mcp_resources×2]
    qwen-code/glm-5.2/cli -> mixed     [web_fetch×6, run_shell_command×1]
    qwen-code/glm-5.2/mcp -> mixed     [mcp__github__get_file_contents×12, tool_search×1, mcp__github__list_tags×1]
    qwen-code/gpt-5-mini/mcp -> pure-cli  [run_shell_command×7, agent×1]
    qwen-code/gpt-5.1/mcp -> no-tools  []
    qwen-code/gpt-5.2/mcp -> no-tools  []
    qwen-code/gpt-5.6-luna/cli -> web-api   [web_fetch×5]
    qwen-code/gpt-5.6-luna/mcp -> mixed     [mcp__github__get_file_contents×12, tool_search×3, mcp__github__list_tags×1]
    qwen-code/gpt-5.6-sol/cli -> web-api   [web_fetch×5, tool_search×1]
    qwen-code/gpt-5.6-terra/cli -> web-api   [web_fetch×5]
    qwen-code/qwen3.6:27b/cli -> web-api   [web_fetch×15]

========================================================================
Q1  Holding scaffolding and model fixed, which surface costs less?
========================================================================

  all pairs with both arms  (n=19)
    median MCP/CLI = 1.71×   CLI cheaper in 13/19 pairs
    range 0.27×–7.41×
      codex/gpt-5.2               160,294 ->   43,127   0.27×  MCP cheaper
      codex/gpt-5-mini            121,552 ->   64,907   0.53×  MCP cheaper
      qwen-code/gpt-5-mini        405,321 ->  291,964   0.72×  MCP cheaper
      codex/gpt-5.6-luna           25,046 ->   18,140   0.72×  MCP cheaper
      qwen-code/qwen3.6:27b       271,545 ->  260,276   0.96×  MCP cheaper
      codex/qwen3.6:27b            63,405 ->   61,228   0.97×  MCP cheaper
      codex/qwen3.5:122b           71,507 ->   77,622   1.09×  
      codex/gpt-5.6-terra          28,426 ->   30,997   1.09×  
      codex/glm-5.2                39,284 ->   59,293   1.51×  
      qwen-code/gpt-5.6-sol       133,654 ->  228,894   1.71×  
      qwen-code/glm-5.2           142,889 ->  247,723   1.73×  
      qwen-code/gpt-5.6-terra     106,225 ->  189,434   1.78×  
      claude-code/fable-5          66,696 ->  131,094   1.97×  
      claude-code/opus-5           66,676 ->  150,827   2.26×  
      claude-code/sonnet-5         99,825 ->  349,309   3.50×  
      qwen-code/qwen3.5:122b       73,324 ->  289,545   3.95×  
      codex/gpt-5.1                61,169 ->  354,000   5.79×  
      qwen-code/gpt-5.6-luna       77,984 ->  555,763   7.13×  
      codex/gpt-5.6-sol            28,631 ->  212,213   7.41×  

  pairs where BOTH runs were method-pure  (n=2)
    median MCP/CLI = 6.60×   CLI cheaper in 2/2 pairs
    range 5.79×–7.41×
      codex/gpt-5.1                61,169 ->  354,000   5.79×  
      codex/gpt-5.6-sol            28,631 ->  212,213   7.41×  

========================================================================
Q2  Does one surface complete the task where the other does not?
========================================================================
  method-pure pairs: 2
    both surfaces completed fully : 2
    only CLI completed            : 0  []
    only MCP completed            : 0  []
    neither                       : 0

========================================================================
Q3  What path does each scaffolding take, and does orchestration pay?
========================================================================

  scaffolding   runs  med tokens med calls orch calls full done
  pi               9       7,355         6          0      9/9
  codex           18      61,198         8          0     15/18
  claude-code      6     115,460         7          6      5/6
  qwen-code       14     238,308        14          8      7/14

  Same model, every scaffolding, CLI arm only:
    glm-5.2                  pi    4,843   ...  qwen-code  142,889   ×30
    gpt-5-mini               pi   19,089   ...  qwen-code  405,321   ×21
    gpt-5.6-luna             pi    6,766   ...  qwen-code   77,984   ×12
    gpt-5.6-sol              pi    4,725   ...  qwen-code  133,654   ×28
    gpt-5.6-terra            pi    4,398   ...  qwen-code  106,225   ×24
    qwen3.5:122b             pi   18,262   ...  qwen-code   73,324   ×4
    qwen3.6:27b              pi   31,758   ...  qwen-code  271,545   ×9
