| Harness | MCP client | Runs | Median tokens | Relative | Completed |
|---|:--:|---:|---:|---:|---:|
| pi | no | 4 | 14,660 | ×1.0 | 4/4 |
| tau | no | 4 | 16,459 | ×1.1 | 4/4 |
| hermes | yes | 8 | 75,054 | ×5.1 | 7/8 |
| codex | yes | 8 | 141,918 | ×9.7 | 6/8 |
| qwen-code | yes | 8 | 258,405 | ×17.6 | 7/8 |
| claude-code | yes | 2 | 450,360 | ×30.7 | 1/2 |

| Harness | Model | Arm | Tokens | Cache | Calls | Offered | Completed |
|---|---|:--:|---:|---:|---:|---:|---:|
| claude-code | sonnet-5 | cli | 543,139 | 97% | 14 | — | 100.0% |
| claude-code | sonnet-5 | mcp | 357,580 | 95% | 10 | — | 25.0% |
| codex | glm-5.2 | cli | 102,031 | 99% | 20 | — | 100.0% |
| codex | glm-5.2 | mcp | 231,797 | 94% | 30 | — | 100.0% |
| codex | gpt-5.6-luna | cli | 81,510 | 88% | 14 | — | 100.0% |
| codex | gpt-5.6-luna | mcp | 189,489 | 87% | 10 | — | 25.0% |
| codex | gpt-5.6-terra | cli | 39,378 | 73% | 6 | — | 100.0% |
| codex | gpt-5.6-terra | mcp | 181,806 | 86% | 10 | — | 25.0% |
| codex | qwen3.6:27b | cli | 83,247 | 0% | 16 | — | 100.0% |
| codex | qwen3.6:27b | mcp | 2,418,828 | 0% | 108 | — | 100.0% |
| hermes | glm-5.2 | cli | 74,755 | 96% | 15 | 6 | 100.0% |
| hermes | glm-5.2 | mcp | 45,875 | 82% | 12 | 7 | 100.0% |
| hermes | gpt-5.6-luna | cli | 73,655 | 88% | — | 6 | 75.0% |
| hermes | gpt-5.6-luna | mcp | 75,352 | 86% | — | 7 | 100.0% |
| hermes | gpt-5.6-terra | cli | 91,409 | 90% | — | 6 | 100.0% |
| hermes | gpt-5.6-terra | mcp | 81,222 | 89% | — | 7 | 100.0% |
| hermes | qwen3.6:27b | cli | 83,954 | — | 14 | 6 | 100.0% |
| hermes | qwen3.6:27b | mcp | 66,320 | — | 14 | 7 | 100.0% |
| pi | glm-5.2 | cli | 13,588 | 96% | 6 | — | 100.0% |
| pi | glm-5.2 | mcp | void | | | | pi ships no MCP client |
| pi | gpt-5.6-luna | cli | 15,731 | 87% | 13 | — | 100.0% |
| pi | gpt-5.6-luna | mcp | void | | | | pi ships no MCP client |
| pi | gpt-5.6-terra | cli | 10,892 | 88% | 7 | — | 100.0% |
| pi | gpt-5.6-terra | mcp | void | | | | pi ships no MCP client |
| pi | qwen3.6:27b | cli | 25,548 | 0% | 10 | — | 100.0% |
| pi | qwen3.6:27b | mcp | void | | | | pi ships no MCP client |
| qwen-code | glm-5.2 | cli | 322,868 | 99% | 11 | — | 100.0% |
| qwen-code | glm-5.2 | mcp | 170,937 | 98% | 8 | — | 50.0% |
| qwen-code | gpt-5.6-luna | cli | 288,808 | 89% | 15 | — | 100.0% |
| qwen-code | gpt-5.6-luna | mcp | 187,725 | 68% | 8 | — | 100.0% |
| qwen-code | gpt-5.6-terra | cli | 228,002 | 87% | 9 | — | 100.0% |
| qwen-code | gpt-5.6-terra | mcp | 219,075 | 72% | 8 | — | 100.0% |
| qwen-code | qwen3.6:27b | cli | 306,490 | 0% | 11 | — | 100.0% |
| qwen-code | qwen3.6:27b | mcp | 397,922 | 0% | 10 | — | 100.0% |
| tau | glm-5.2 | cli | 15,502 | 86% | 7 | — | 100.0% |
| tau | glm-5.2 | mcp | void | | | | tau ships no MCP client |
| tau | gpt-5.6-luna | cli | 11,554 | 77% | 6 | — | 100.0% |
| tau | gpt-5.6-luna | mcp | void | | | | tau ships no MCP client |
| tau | gpt-5.6-terra | cli | 27,412 | 76% | 11 | — | 100.0% |
| tau | gpt-5.6-terra | mcp | void | | | | tau ships no MCP client |
| tau | qwen3.6:27b | cli | 17,416 | — | 7 | — | 100.0% |
| tau | qwen3.6:27b | mcp | void | | | | tau ships no MCP client |
