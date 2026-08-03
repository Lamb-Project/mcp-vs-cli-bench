#!/usr/bin/env bash
# Re-run every codex cell with per-run CODEX_HOME isolation.
# The global mcp registration leaked into CLI arms; three CLI runs called MCP
# tools. Both arms are re-run because the fix changes config for both.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)"
while pgrep -f "bench.runner" >/dev/null 2>&1; do sleep 20; done
PYTHONPATH="$PWD" python3 -u -m bench.runner --budget 5.00 --timeout 1800 \
    --only codex --out results/runs-codex-clean.jsonl >> results/codex-rerun.log 2>&1
echo "CODEX RERUN DONE"
