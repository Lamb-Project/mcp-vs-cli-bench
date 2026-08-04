
==============================================================================
A. When MCP costs more, where does the extra go?
==============================================================================

  cell                       ratio   Δtokens  Δcalls CLI t/call MCP t/call  MCP init
  codex/gpt-5.6-sol           7.41   183,582     +34      7,158      5,585   212,213
  qwen-code/gpt-5.6-luna      7.13   477,779     +12     15,597     32,692   555,763
  codex/gpt-5.1               5.79   292,831     +26     30,584     12,643   354,000
  qwen-code/qwen3.5:122b      3.95   216,221     +17          —     17,032   289,545
  claude-code/sonnet-5        3.50   249,484      +8     16,638     24,951    45,462
  claude-code/opus-5          2.26    84,151      +4     16,669     18,853    26,671
  claude-code/fable-5         1.97    64,398      +4     13,339     14,566    28,508
  qwen-code/gpt-5.6-terra     1.78    83,209     +10     21,245     12,629   189,434
  qwen-code/glm-5.2           1.73   104,834      +8     20,413     16,515   247,723
  qwen-code/gpt-5.6-sol       1.71    95,240      +9     22,276     15,260   228,894
  codex/glm-5.2               1.51    20,009      +6      6,547      4,941    59,293
  codex/gpt-5.6-terra         1.09     2,571      +0      7,106      7,749    30,997
  codex/qwen3.5:122b          1.09     6,115      +0      5,108      5,544    77,622

  attribution of the extra MCP tokens:
    codex/gpt-5.6-sol          first request  +183,582 (100.0%)   everything after        +0 (  0.0%)
    qwen-code/gpt-5.6-luna     first request  +477,779 (100.0%)   everything after        +0 (  0.0%)
    codex/gpt-5.1              first request  +292,831 (100.0%)   everything after        +0 (  0.0%)
    qwen-code/qwen3.5:122b     first request  +216,221 (100.0%)   everything after        +0 (  0.0%)
    claude-code/sonnet-5       first request   +11,735 (  4.7%)   everything after  +237,749 ( 95.3%)
    claude-code/opus-5         first request    +3,212 (  3.8%)   everything after   +80,939 ( 96.2%)
    claude-code/fable-5        first request    +5,705 (  8.9%)   everything after   +58,693 ( 91.1%)
    qwen-code/gpt-5.6-terra    first request   +83,209 (100.0%)   everything after        +0 (  0.0%)
    qwen-code/glm-5.2          first request  +104,834 (100.0%)   everything after        +0 (  0.0%)
    qwen-code/gpt-5.6-sol      first request   +95,240 (100.0%)   everything after        +0 (  0.0%)
    codex/glm-5.2              first request   +20,009 (100.0%)   everything after        +0 (  0.0%)
    codex/gpt-5.6-terra        first request    +2,571 (100.0%)   everything after        +0 (  0.0%)
    codex/qwen3.5:122b         first request    +6,115 (100.0%)   everything after        +0 (  0.0%)

==============================================================================
B. When the CLI costs more (ratio < 1), what is it spending on?
==============================================================================

  cell                       ratio   CLI tok CLIcalls CLI t/call  what the CLI arm called
  codex/gpt-5.2               0.27   160,294       22      7,286  shell:aawd-e1-fixture×18, shell:ls×2
                                                                  MCP side: shell:set×2  [pure-cli]
  codex/gpt-5-mini            0.53   121,552       14      8,682  shell:curl×12, shell:git×2
                                                                  MCP side: —  [no-tools]
  qwen-code/gpt-5-mini        0.72   405,321       13     31,179  run_shell_command×13
                                                                  MCP side: run_shell_command×7, agent×1  [pure-cli]
  codex/gpt-5.6-luna          0.72    25,046        2     12,523  shell:set×2
                                                                  MCP side: shell:set×2  [pure-cli]
  qwen-code/qwen3.6:27b       0.96   271,545       15     18,103  web_fetch×15
                                                                  MCP side: mcp__github__get_file_contents×12, mcp__github__get_me×1  [pure-mcp]
  codex/qwen3.6:27b           0.97    63,405       14      4,529  shell:git×6, shell:ls×4
                                                                  MCP side: shell:curl×8, mcp__list_mcp_resources×2  [mixed]

==============================================================================
C. Uncached tokens — what actually had to be processed
==============================================================================

  cell                         CLI pre   MCP pre  pre ratio  tot ratio  CLI hit%  MCP hit%
  codex/glm-5.2                  7,823     1,549       0.20       1.51     80.1%     97.4%
  qwen-code/gpt-5-mini          27,209     5,756       0.21       0.72     93.3%     98.0%
  qwen-code/glm-5.2             14,563     6,710       0.46       1.73     89.8%     97.3%
  qwen-code/qwen3.6:27b        271,545   260,276       0.96       0.96      0.0%      0.0%
  codex/qwen3.6:27b             63,405    61,228       0.97       0.97      0.0%      0.0%
  codex/gpt-5.2                 14,374    15,351       1.07       0.27     91.0%     64.4%
  codex/qwen3.5:122b            71,507    77,622       1.09       1.09      0.0%      0.0%
  codex/gpt-5.6-luna             8,776     9,545       1.09       0.72     65.0%     47.4%
  codex/gpt-5.6-terra            9,752    10,629       1.09       1.09     65.7%     65.7%
  qwen-code/gpt-5.6-terra       50,611    62,383       1.23       1.78     52.4%     67.1%
  qwen-code/gpt-5.6-sol         50,486    64,209       1.27       1.71     62.2%     71.9%
  claude-code/opus-5             8,195    11,412       1.39       2.26     87.7%     92.4%
  claude-code/fable-5            7,556    13,264       1.76       1.97     88.7%     89.9%
  qwen-code/gpt-5.6-luna        50,420   102,674       2.04       7.13     35.3%     81.5%
  claude-code/sonnet-5          10,047    21,794       2.17       3.50     89.9%     93.8%
  codex/gpt-5.1                 34,161    74,960       2.19       5.79     44.2%     78.8%
  codex/gpt-5-mini              25,296    64,907       2.57       0.53     79.2%      0.0%
  codex/gpt-5.6-sol              9,852    25,304       2.57       7.41     65.6%     88.1%
  qwen-code/qwen3.5:122b        73,324   289,545       3.95       3.95      0.0%      0.0%

  median uncached ratio 1.23×   median total ratio 1.71×
  Caching does not close the gap: it discounts both arms similarly,
  so the uncached comparison tracks the total one.
