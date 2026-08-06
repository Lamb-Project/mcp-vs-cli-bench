#!/usr/bin/env bash
# Three repetitions of every local-model cell, to put error bars on the headline
# table. Local inference is free of marginal cost, so the only price is
# wall-clock. Each repetition writes its own file; consolidation happens after.
set -uo pipefail
cd "$(dirname "$0")/.."
export E1_USAGE_LOG="$PWD/results/usage-rerun.jsonl"
export BENCH_KEY=sk-e1-local
export PYTHONPATH="$HOME/Code/tau/src"
# codex and qwen live under the nvm node the harness was built against. A
# detached shell does not source nvm, so without this the runner dies on
# FileNotFoundError partway through and the repetition silently truncates.
export PATH="$HOME/.nvm/versions/node/v24.18.1/bin:$HOME/.nvm/versions/node/v22.18.0/bin:$HOME/.local/bin:$PATH"
for b in codex qwen pi claude; do
  command -v "$b" >/dev/null || { echo "FATAL: $b not on PATH" >&2; exit 1; }
done
for rep in 1 2 3; do
  for model in glm-5.2 "qwen3.6:27b"; do
    echo "=== repetition $rep — $model ==="
    python3 -m bench.runner --only "$model" \
      --out "results/runs-local-rep${rep}.jsonl" --timeout 2400
  done
done
echo "=== all repetitions complete ==="
