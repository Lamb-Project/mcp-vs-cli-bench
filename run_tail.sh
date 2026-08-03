#!/usr/bin/env bash
# Remaining re-runs, strictly sequential in one process — no cross-script waiting.
# Two chained scripts polling for each other deadlocked; one process cannot.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)" E1_USAGE_LOG="$PWD/results/usage.jsonl"

echo "--- qwen-code re-run (max_tokens fix via proxy) ---"
E1_RUN_TAG="qwen-clean" PYTHONPATH="$PWD" python3 -u -m bench.runner \
    --budget 5.00 --timeout 1800 --only qwen-code --out results/runs-qwen-clean.jsonl \
    >> results/qwen-rerun.log 2>&1

echo "--- codex gpt-5.x re-run (contaminated era) ---"
for m in gpt-5.2 gpt-5.1 gpt-5-mini; do
  E1_RUN_TAG="codex5x-$m" PYTHONPATH="$PWD" python3 -u -m bench.runner \
      --budget 5.00 --timeout 1800 --only "$m" --out results/runs-codex5x-clean.jsonl \
      >> results/codex5x.log 2>&1
done
echo "=== TAIL RUNS COMPLETE ==="
