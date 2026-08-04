#!/usr/bin/env bash
# Experiment 2: private fixture, isolated arms, write workflow.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)"
export E1_USAGE_LOG="$PWD/results/usage-e3.jsonl"
export MCP_FIXTURE_TOKEN="$(security find-generic-password -a mcp-bench -s mcp-bench-e2-token -w)"
PYTHONPATH="$PWD" python3 -u -m bench.runner --budget 2.00 --timeout 2400 \
    --out results/runs-e3.jsonl >> results/e3.log 2>&1
echo "EXPERIMENT 2 COMPLETE"
