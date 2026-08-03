#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
export NVM_DIR="$HOME/.nvm"; . "$(brew --prefix nvm)/nvm.sh" >/dev/null 2>&1; nvm use default >/dev/null 2>&1
export E1_USAGE_LOG="$PWD/results/usage.jsonl" E1_RUN_TAG="pi-fix"
PYTHONPATH="$PWD" python3 -u - <<'PY'
from pathlib import Path
from bench.adapters.impl import ADAPTERS
from bench.runner import gh_token, RESULTS
from bench.costs import theoretical_cost
import json
wd=RESULTS/'runs'; tok=gh_token(); out=RESULTS/'runs-pi-fix.jsonl'
done={json.loads(l)['model'] for l in out.read_text().splitlines() if l.strip()} if out.exists() else set()
for m in ('gpt-5.6-sol','gpt-5.6-luna','gpt-5.6-terra'):
    if m in done:
        print(f'  pi/{m} already recorded', flush=True); continue
    a=ADAPTERS['pi'](wd, str(Path.cwd()/'bin'/'github-mcp-server'), tok)
    r=a.run(m,'cli',timeout=900)
    if r.total_input_tokens:
        r.theoretical_cost_usd=theoretical_cost(m,r.total_input_tokens or 0,r.total_output_tokens or 0,r.cached_tokens or 0).total_usd
    with out.open('a') as fh: fh.write(r.to_json()+chr(10))
    print(f'  pi/{m} done={r.completion_pct} tools={r.tool_calls} in={r.total_input_tokens}', flush=True)
PY
echo "PI FIX COMPLETE"
