#!/usr/bin/env bash
# One-shot setup for the benchmark. Idempotent; safe to re-run.
#
# Installs the four scaffoldings, fetches the MCP server binary, creates the
# proxy environment, and checks the preconditions that silently change results
# if they are wrong. It deliberately refuses to proceed on a bad precondition
# rather than producing numbers that will not reproduce.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
fail=0

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  WARN  %s\n' "$*"; }
bad()  { printf '  FAIL  %s\n' "$*"; fail=1; }

say "1. Node and the scaffoldings"
if ! command -v node >/dev/null; then
    bad "node not found — install Node >= 22 (qwen-code requires it)"
else
    v=$(node --version | tr -d 'v' | cut -d. -f1)
    [ "$v" -ge 22 ] && ok "node $(node --version)" || bad "node >= 22 required, found $(node --version)"
fi

for pkg in "@qwen-code/qwen-code:qwen" "@openai/codex:codex" "@mariozechner/pi:pi"; do
    name="${pkg%%:*}"; bin="${pkg##*:}"
    if command -v "$bin" >/dev/null; then ok "$bin present"
    else
        echo "  installing $name ..."
        npm install -g "$name" >/dev/null 2>&1 && ok "$bin installed" || bad "$bin install failed"
    fi
done
command -v claude >/dev/null && ok "claude present" \
    || warn "claude not found — Claude Code cells will be skipped (install separately)"

say "2. GitHub MCP server"
if [ -x bin/github-mcp-server ]; then
    ok "binary present ($(bin/github-mcp-server --version 2>/dev/null | head -1))"
else
    mkdir -p bin
    case "$(uname -s)-$(uname -m)" in
        Darwin-arm64) asset="github-mcp-server_Darwin_arm64.tar.gz" ;;
        Darwin-x86_64) asset="github-mcp-server_Darwin_x86_64.tar.gz" ;;
        Linux-x86_64) asset="github-mcp-server_Linux_x86_64.tar.gz" ;;
        Linux-aarch64|Linux-arm64) asset="github-mcp-server_Linux_arm64.tar.gz" ;;
        *) bad "no prebuilt MCP server for $(uname -s)-$(uname -m)"; asset="" ;;
    esac
    if [ -n "$asset" ]; then
        (cd bin && gh release download v1.8.0 --repo github/github-mcp-server \
            --pattern "$asset" --clobber >/dev/null 2>&1 && tar xzf "$asset") \
            && ok "MCP server v1.8.0 fetched" || bad "MCP server download failed"
    fi
fi

say "3. Proxy environment"
if command -v uv >/dev/null; then
    [ -d .venv-litellm ] || uv venv --python 3.12 .venv-litellm >/dev/null 2>&1
    # litellm 1.95 declares fastapi>=0.136.3,<1.0 but versions above 0.136.3
    # removed a symbol it imports; the pin is required, not cosmetic.
    uv pip install --python .venv-litellm/bin/python --quiet \
        'litellm[proxy]' 'fastapi==0.136.3' >/dev/null 2>&1 \
        && ok "litellm installed (fastapi pinned to 0.136.3)" || bad "litellm install failed"
    cp setup/usage_logger.py .venv-litellm/lib/python*/site-packages/ 2>/dev/null \
        && ok "usage callback installed"
else
    bad "uv not found — needed to build the proxy environment"
fi

say "4. Credentials"
gh auth token >/dev/null 2>&1 && ok "gh authenticated" || bad "run: gh auth login"
[ -n "${OPENAI_API_KEY:-}" ] && ok "OPENAI_API_KEY set" \
    || warn "OPENAI_API_KEY unset — hosted-model cells will fail"

say "5. Preconditions that change results if wrong"
if pgrep -f llama-server >/dev/null 2>&1; then
    if ps -o command= -p "$(pgrep -f llama-server | head -1)" | grep -q -- "--reasoning off"; then
        ok "llama-server running with --reasoning off"
    else
        bad "llama-server is running WITHOUT --reasoning off — thinking can run away and will not reproduce"
    fi
else
    warn "llama-server not running — local-model cells will fail"
fi
python3 - <<'PY' && ok "fixture reachable at its pinned tag" || warn "fixture tag unreachable"
import json,subprocess,sys
r=subprocess.run(["gh","api","repos/Lamb-Project/aawd-e1-fixture/tags"],
                 capture_output=True,text=True)
sys.exit(0 if r.returncode==0 and "fixture-v1" in r.stdout else 1)
PY

say "Result"
if [ "$fail" -eq 0 ]; then
    echo "  Setup complete. Next:"
    echo "    python setup/configure_pi.py                # register pi providers"
    echo "    .venv-litellm/bin/litellm --config setup/litellm_config.yaml --port 4000 &"
    echo "    python -m bench.runner --estimate-only      # check spend first"
    echo "    python -m bench.runner --budget 5.00"
else
    echo "  Setup incomplete — fix the FAIL lines above before running."
    exit 1
fi
