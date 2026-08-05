**Table 1 — Experiment 1 (re-run, uniform routing, public fixture)**

| Scaffolding | Model | Arm | Total tokens | Uncached | Calls | Pure? | Completion |
|---|---|---|---:|---:|---:|:--:|---:|
| claude-code | opus-5 | CLI | 67,270 | 8,607 | 5 | ✔ | 100.0% |
| claude-code | opus-5 | MCP | 153,196 | 12,539 | 8 | ✗ mixed | 100.0% |
| claude-code | sonnet-5 | CLI | 99,771 | 10,015 | 6 | ✔ | 100.0% |
| claude-code | sonnet-5 | MCP | 258,254 | 15,268 | 12 | ✗ mixed | 100.0% |
| codex | glm-5.2 | CLI | 39,577 | 599 | 6 | ✔ | 100.0% |
| codex | glm-5.2 | MCP | 32,634 | 8,141 | 4 | ✗ pure-cli | 100.0% |
| codex | gpt-5.6-luna | CLI | 41,784 | 17,372 | 4 | ✔ | 100.0% |
| codex | gpt-5.6-luna | MCP | 63,232 | 18,505 | 4 | ✗ pure-cli | 100.0% |
| codex | gpt-5.6-terra | CLI | 39,356 | 10,436 | 4 | ✔ | 100.0% |
| codex | gpt-5.6-terra | MCP | 42,363 | 11,608 | 6 | ✗ pure-cli | 100.0% |
| codex | qwen3.5:122b | CLI | 102,369 | 102,369 | 22 | ✔ | 100.0% |
| codex | qwen3.5:122b | MCP | 113,774 | 113,774 | 18 | ✗ mixed | 100.0% |
| codex | qwen3.6:27b | CLI | 30,204 | 30,204 | 12 | ✔ | 100.0% |
| codex | qwen3.6:27b | MCP | 188,853 | 188,853 | 20 | ✗ mixed | 100.0% |
| pi | glm-5.2 | CLI | 6,540 | 258 | 3 | ✔ | 100.0% |
| pi | glm-5.2 | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | gpt-5.6-luna | CLI | 4,202 | 540 | 3 | ✔ | 100.0% |
| pi | gpt-5.6-luna | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | gpt-5.6-terra | CLI | 4,417 | 737 | 4 | ✔ | 100.0% |
| pi | gpt-5.6-terra | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | qwen3.5:122b | CLI | 16,243 | 16,243 | 9 | ✔ | 100.0% |
| pi | qwen3.5:122b | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | qwen3.6:27b | CLI | 8,138 | 8,138 | 7 | ✔ | 100.0% |
| pi | qwen3.6:27b | MCP | ⛔ | | | | *pi ships no MCP client* |
| qwen-code | glm-5.2 | CLI | 171,736 | 10,781 | 6 | ✗ mixed | 100.0% |
| qwen-code | glm-5.2 | MCP | 249,241 | 3,418 | 15 | ✔ | 80.0% |
| qwen-code | gpt-5.6-luna | CLI | 109,787 | 54,186 | 7 | ✗ web-api | 100.0% |
| qwen-code | gpt-5.6-luna | MCP | 286,892 | 94,629 | 16 | ✔ | 100.0% |
| qwen-code | gpt-5.6-terra | CLI | 109,073 | 53,408 | 6 | ✗ web-api | 100.0% |
| qwen-code | gpt-5.6-terra | MCP | 189,453 | 62,386 | 15 | ✔ | 80.0% |
| qwen-code | qwen3.5:122b | CLI | 66,340 | 66,340 | 1 | ✗ no-tools | 0.0% |
| qwen-code | qwen3.5:122b | MCP | 91,646 | 91,646 | 0 | ✗ no-tools | 0.0% |
| qwen-code | qwen3.6:27b | CLI | 269,804 | 269,804 | 15 | ✗ web-api | 100.0% |
| qwen-code | qwen3.6:27b | MCP | 260,789 | 260,789 | 15 | ✔ | 80.0% |

**Table 2 — Experiment 3 (private fixture, isolated arms)**

| Scaffolding | Model | Arm | Total tokens | Uncached | Calls | Pure? | Completion |
|---|---|---|---:|---:|---:|:--:|---:|
| claude-code | sonnet-5 | CLI | 543,139 | 15,512 | 14 | ✔ | 80.0% |
| claude-code | sonnet-5 | MCP | 357,580 | 18,838 | 10 | ✗ mixed | 20.0% |
| codex | glm-5.2 | CLI | 102,031 | 1,158 | 20 | ✔ | 80.0% |
| codex | glm-5.2 | MCP | 231,797 | 15,168 | 30 | ✗ mixed | 80.0% |
| codex | gpt-5.6-luna | CLI | 81,510 | 10,159 | 14 | ✔ | 80.0% |
| codex | gpt-5.6-luna | MCP | 189,489 | 24,430 | 10 | ✔ | 20.0% |
| codex | gpt-5.6-terra | CLI | 39,378 | 10,497 | 6 | ✔ | 80.0% |
| codex | gpt-5.6-terra | MCP | 181,806 | 25,937 | 10 | ✗ mixed | 20.0% |
| codex | qwen3.6:27b | CLI | 83,247 | 83,247 | 16 | ✔ | 80.0% |
| codex | qwen3.6:27b | MCP | 2,418,828 | 2,418,828 | 108 | ✗ mixed | 80.0% |
| pi | glm-5.2 | CLI | 13,588 | 544 | 6 | ✔ | 80.0% |
| pi | glm-5.2 | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | gpt-5.6-luna | CLI | 15,731 | 2,081 | 13 | ✔ | 80.0% |
| pi | gpt-5.6-luna | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | gpt-5.6-terra | CLI | 10,892 | 1,260 | 7 | ✔ | 80.0% |
| pi | gpt-5.6-terra | MCP | ⛔ | | | | *pi ships no MCP client* |
| pi | qwen3.6:27b | CLI | ⛔ | | | | *reasoning output present — thinkin* |
| pi | qwen3.6:27b | MCP | ⛔ | | | | *pi ships no MCP client* |
| qwen-code | glm-5.2 | CLI | 322,868 | 3,096 | 11 | ✔ | 80.0% |
| qwen-code | glm-5.2 | MCP | 170,937 | 4,275 | 8 | ✔ | 40.0% |
| qwen-code | gpt-5.6-luna | CLI | 288,808 | 30,946 | 15 | ✔ | 80.0% |
| qwen-code | gpt-5.6-luna | MCP | 187,725 | 60,957 | 8 | ✔ | 80.0% |
| qwen-code | gpt-5.6-terra | CLI | 228,002 | 30,261 | 9 | ✔ | 80.0% |
| qwen-code | gpt-5.6-terra | MCP | 219,075 | 60,933 | 8 | ✔ | 80.0% |
| qwen-code | qwen3.6:27b | CLI | 306,490 | 306,490 | 11 | ✔ | 80.0% |
| qwen-code | qwen3.6:27b | MCP | 397,922 | 397,922 | 10 | ✔ | 80.0% |
