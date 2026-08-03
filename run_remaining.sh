#!/usr/bin/env bash
# Remaining work, strictly sequential: the gpt-5.6 cells, then a clean codex
# re-run on both arms. Sequential because the local models share one GPU with
# --parallel 1, and because two runners would race on the results file.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)"
export E1_USAGE_LOG="$PWD/results/usage.jsonl"

for m in gpt-5.6-sol gpt-5.6-luna gpt-5.6-terra; do
  E1_RUN_TAG="$m" PYTHONPATH="$PWD" python3 -u -m bench.runner \
      --budget 5.00 --timeout 1800 --only "$m" --out results/runs.jsonl \
      >> results/full56.log 2>&1
done
echo "=== gpt-5.6 cells done ==="

E1_RUN_TAG="codex-clean" PYTHONPATH="$PWD" python3 -u -m bench.runner \
    --budget 5.00 --timeout 1800 --only codex --out results/runs-codex-clean.jsonl \
    >> results/codex-rerun.log 2>&1
echo "=== codex clean re-run done ==="
