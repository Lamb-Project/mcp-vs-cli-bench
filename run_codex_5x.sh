#!/usr/bin/env bash
# The codex re-run covered gpt-5.6 and the local models, because the matrix had
# already been switched to the 5.6 line. The gpt-5.x cells therefore remain from
# the contaminated era — two of their CLI arms called MCP tools, and one MCP arm
# delegated to sub-agents. Re-run them under isolation and through the proxy so
# the dataset is uniform.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)" E1_USAGE_LOG="$PWD/results/usage.jsonl"
while pgrep -f "run_qwen_hosted.sh|bench.runner" >/dev/null 2>&1; do sleep 30; done
for m in gpt-5.2 gpt-5.1 gpt-5-mini; do
  E1_RUN_TAG="codex5x-$m" PYTHONPATH="$PWD" python3 -u -m bench.runner \
      --budget 5.00 --timeout 1800 --only "$m" --out results/runs-codex5x-clean.jsonl \
      >> results/codex5x.log 2>&1
done
echo "=== codex gpt-5.x re-run done ==="
