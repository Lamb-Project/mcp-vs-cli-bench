#!/usr/bin/env bash
# Wait for the in-flight matrix to exit, then run the gpt-5.6 cells.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)"
while pgrep -f "bench.runner" >/dev/null 2>&1; do sleep 20; done
# gpt-5.x rows already collected are kept; append the 5.6 rows to the same file
for m in gpt-5.6-sol gpt-5.6-luna gpt-5.6-terra; do
  PYTHONPATH="$PWD" python3 -u -m bench.runner --budget 5.00 --timeout 1800 \
      --only "$m" --out results/runs.jsonl >> results/full56.log 2>&1
done
echo "GPT-5.6 CELLS DONE"
