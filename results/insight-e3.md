========================================================================
Q0  Did each run use exclusively the method it was assigned?
========================================================================
  assigned CLI : pure-cli=12, void=1
  assigned MCP : mixed=4, pure-mcp=5, void=4

  Runs whose actual behaviour does not match their assignment:
    claude-code/sonnet-5/mcp -> mixed     [Bash×4, mcp__github__get_me×2, ToolSearch×1]
    codex/gpt-5.6-terra/mcp -> mixed     [mcp__search_issues×4, mcp__get_me×2, mcp__get_file_contents×2]
    codex/glm-5.2/mcp -> mixed     [shell:curl×8, shell:echo×6, shell:python3×4]
    codex/qwen3.6:27b/mcp -> mixed     [mcp__read_mcp_resource×28, shell:TOKEN=×14, shell:ls×12]

========================================================================
Q1  Holding scaffolding and model fixed, which surface costs less?
========================================================================

  all pairs with both arms  (n=9)
    median MCP/CLI = 1.30×   CLI cheaper in 5/9 pairs
    range 0.53×–29.06×
      qwen-code/glm-5.2           322,868 ->  170,937   0.53×  MCP cheaper
      qwen-code/gpt-5.6-luna      288,808 ->  187,725   0.65×  MCP cheaper
      claude-code/sonnet-5        543,139 ->  357,580   0.66×  MCP cheaper
      qwen-code/gpt-5.6-terra     228,002 ->  219,075   0.96×  MCP cheaper
      qwen-code/qwen3.6:27b       306,490 ->  397,922   1.30×  
      codex/glm-5.2               102,031 ->  231,797   2.27×  
      codex/gpt-5.6-luna           81,510 ->  189,489   2.32×  
      codex/gpt-5.6-terra          39,378 ->  181,806   4.62×  
      codex/qwen3.6:27b            83,247 -> 2,418,828  29.06×  
  pairs where BOTH runs were method-pure: none

========================================================================
Q2  Does one surface complete the task where the other does not?
========================================================================
  method-pure pairs: 0
    both surfaces completed fully : 0
    only CLI completed            : 0  []
    only MCP completed            : 0  []
    neither                       : 0

========================================================================
Q3  What path does each scaffolding take, and does orchestration pay?
========================================================================

  scaffolding   runs  med tokens med calls orch calls full done
  pi               3      13,588         7          0      0/3
  codex            8     141,918        15          0      0/8
  qwen-code        8     258,405        10          5      0/8
  claude-code      2     450,360        12          1      0/2

  Same model, every scaffolding, CLI arm only:
    glm-5.2                  pi   13,588   ...  qwen-code  322,868   ×24
    gpt-5.6-luna             pi   15,731   ...  qwen-code  288,808   ×18
    gpt-5.6-terra            pi   10,892   ...  qwen-code  228,002   ×21
