#!/usr/bin/env bash
# Experiment 1, re-run with uniform routing.
#
# Every request now crosses the proxy, so one accounting path covers every cell.
# Experiment 1 mixed direct and proxied routing and lost the per-request record
# for the direct cells, which is why the sub-1.0 ratios could not be trusted.
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export OPENAI_API_KEY="$(llm keys get openai)"
export E1_USAGE_LOG="$PWD/results/usage-rerun.jsonl"
PYTHONPATH="$PWD" python3 -u -m bench.runner --budget 5.00 --timeout 2400 \
    --out results/runs-rerun.jsonl >> results/rerun.log 2>&1
echo "EXP1 RERUN COMPLETE"
