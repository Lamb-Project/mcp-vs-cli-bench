#!/usr/bin/env bash
# qwen-code x hosted models failed with 400 "max_tokens is not supported with
# this model; use max_completion_tokens" — qwen-code sends the deprecated
# parameter and the GPT-5 family rejects it. Those cells ran direct to OpenAI;
# re-run them through the proxy, where drop_params handles the mismatch.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)" E1_USAGE_LOG="$PWD/results/usage.jsonl"
while pgrep -f "run_remaining.sh" >/dev/null 2>&1; do sleep 30; done
E1_RUN_TAG="qwen-hosted" PYTHONPATH="$PWD" python3 -u -m bench.runner \
    --budget 5.00 --timeout 1800 --only qwen-code --out results/runs-qwen-clean.jsonl \
    >> results/qwen-rerun.log 2>&1
echo "=== qwen-code re-run done ==="
