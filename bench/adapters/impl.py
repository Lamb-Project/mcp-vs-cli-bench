"""Concrete adapters, written against telemetry shapes verified by discovery.

Field locations were established by running each scaffolding once and inspecting
its output (see bench/discover_shapes.py and results/shapes/), not from
documentation — three of the four document none of this.

Verified shapes:
  claude : one JSON document; usage.{input_tokens,output_tokens,
           cache_read_input_tokens,cache_creation_input_tokens}, usage.iterations[]
           (a genuine per-turn series), total_cost_usd, num_turns, result
  codex  : JSONL; turn.completed carries usage.{input_tokens,output_tokens,
           cached_input_tokens,cache_write_input_tokens}
  pi     : JSONL; turn_end.message.usage.{input,output,cacheRead,cacheWrite}
           plus turn_end.toolResults
  qwen   : one JSON document; per-event usage.{input_tokens,output_tokens,
           cache_read_input_tokens}, aggregated (no per-turn series)
"""
from __future__ import annotations

import json
from pathlib import Path

from bench.adapters.base import Adapter, RunResult, prompt

# Local endpoints. Both are OpenAI-compatible, which is what lets three of the
# four scaffoldings point at them at all.
GLM_BASE = "http://localhost:8000/v1"
OLLAMA_BASE = "http://192.168.1.47:11434/v1"
# Everything goes through the LiteLLM proxy. Sub-agent requests cross it too, so
# proxying is what makes token totals complete when a scaffolding delegates; it
# also enforces the spend ceiling upstream of the harness. The proxy contributes
# no tokens, so this is measurement-neutral.
PROXY_BASE = "http://localhost:4000/v1"
PROXY_KEY = "sk-e1-local"

LOCAL_MODELS = {"glm-5.2": GLM_BASE, "qwen3.5:122b": OLLAMA_BASE,
                "qwen3.6:27b": OLLAMA_BASE}


def endpoint_for(model: str) -> tuple[str, str]:
    """(base_url, api_key) — the proxy, for every model, local or hosted.

    OpenRouter is used only as the published price list for the cost model and
    never as a request path.
    """
    return PROXY_BASE, PROXY_KEY


def openrouter_id(model: str) -> str:
    from bench.costs import PRICES
    return PRICES[model][2] if model in PRICES else model


def _walk_tool_calls(obj, register: dict[str, int], names=("tool_use", "function_call")):
    """Collect tool-call names from any of the four event dialects."""
    if isinstance(obj, dict):
        t = obj.get("type")
        if t in names and obj.get("name"):
            register[obj["name"]] = register.get(obj["name"], 0) + 1
        # codex item dialect
        if t in ("command_execution", "mcp_tool_call", "function_call"):
            nm = obj.get("name") or obj.get("command") or t
            nm = nm if isinstance(nm, str) else t
            register[nm.split()[0][:60]] = register.get(nm.split()[0][:60], 0) + 1
        for v in obj.values():
            _walk_tool_calls(v, register, names)
    elif isinstance(obj, list):
        for v in obj:
            _walk_tool_calls(v, register, names)


class ClaudeCodeAdapter(Adapter):
    name = "claude-code"
    supports_mcp = True

    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        if arm == "mcp":
            cfg = {"mcpServers": {"github": {
                "command": self.mcp_bin, "args": ["stdio"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_PERSONAL_ACCESS_TOKEN"}}}}
            (run_dir / ".mcp.json").write_text(json.dumps(cfg, indent=1))

    # the matrix names models uniformly (sonnet-5); claude takes bare aliases
    ALIAS = {"sonnet-5": "sonnet", "opus-5": "opus", "fable-5": "fable"}

    def command(self, model: str, arm: str) -> list[str]:
        # stream-json (not json): the plain json mode returns only the final
        # result, so tool calls would be invisible and reported as zero
        cmd = ["claude", "-p", prompt(), "--output-format", "stream-json",
               "--verbose", "--model", self.ALIAS.get(model, model),
               "--permission-mode", "bypassPermissions"]
        if arm == "cli":
            cmd += ["--strict-mcp-config"]      # no MCP servers at all
        return cmd

    def parse(self, stdout, stderr, res: RunResult) -> RunResult:
        events = [json.loads(l) for l in stdout.splitlines()
                  if l.strip().startswith("{")]
        doc = next((e for e in reversed(events) if e.get("type") == "result"),
                   events[-1] if events else {})
        u = doc.get("usage") or {}
        res.total_input_tokens = (u.get("input_tokens") or 0) + \
            (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
        res.total_output_tokens = u.get("output_tokens")
        res.cached_tokens = u.get("cache_read_input_tokens")
        iters = u.get("iterations") or []
        if iters:
            first = iters[0]
            res.initial_tokens = (first.get("input_tokens") or 0) + \
                (first.get("cache_read_input_tokens") or 0) + \
                (first.get("cache_creation_input_tokens") or 0)
        res.answer = doc.get("result")
        res.notes.append(f"claude-reported billed cost ${doc.get('total_cost_usd')}")
        reg: dict[str, int] = {}
        _walk_tool_calls(events, reg)
        res.tool_register = reg
        res.tool_calls = sum(reg.values())
        return res


class CodexAdapter(Adapter):
    name = "codex"
    supports_mcp = True


    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        # CODEX_HOME per run. `codex mcp add` writes to the *global* config, so
        # a server registered for an MCP arm stayed attached during the CLI arms
        # too — one CLI run was observed calling MCP tools. Isolating the config
        # directory makes each cell independent and the CLI arm genuinely
        # MCP-free.
        self._home = run_dir / ".codex"
        self._home.mkdir(parents=True, exist_ok=True)
        if arm == "mcp":
            cfg = ('[mcp_servers.github]\n'
                   f'command = "{self.mcp_bin}"\n'
                   'args = ["stdio"]\n')
            (self._home / "config.toml").write_text(cfg)
        else:
            (self._home / "config.toml").write_text("")   # explicitly no servers

    def command(self, model: str, arm: str) -> list[str]:
        base, _ = endpoint_for(model)
        mid = model            # plain ids on both local and OpenAI endpoints
        cmd = ["codex", "exec", "--json", "--skip-git-repo-check",
               "-c", 'model_provider="bench"',
               "-c", 'model_providers.bench.name="bench"',
               "-c", f'model_providers.bench.base_url="{base}"',
               "-c", 'model_providers.bench.env_key="BENCH_KEY"',
               # codex defaults to the Responses API; OpenRouter and llama-server
               # both speak chat/completions, so pin the wire protocol
               "-c", 'model_reasoning_effort="low"',
               "-m", mid,
               "--dangerously-bypass-approvals-and-sandbox"]
        cmd += [prompt()]
        return cmd

    def env(self, model: str) -> dict[str, str]:
        env = super().env(model)
        _, key = endpoint_for(model)
        env["BENCH_KEY"] = key or "local"
        home = getattr(self, "_home", None)
        if home is not None:
            env["CODEX_HOME"] = str(home)
        return env

    def parse(self, stdout, stderr, res: RunResult) -> RunResult:
        events = [json.loads(l) for l in stdout.splitlines()
                  if l.strip().startswith("{")]
        usages, texts = [], []
        for e in events:
            u = e.get("usage")
            if isinstance(u, dict) and u.get("input_tokens") is not None:
                usages.append(u)
            item = e.get("item") or {}
            if item.get("type") in ("assistant_message", "agent_message"):
                txt = item.get("text") or item.get("content")
                if isinstance(txt, str):
                    texts.append(txt)
        if usages:
            last = usages[-1]
            res.total_input_tokens = last.get("input_tokens")
            res.total_output_tokens = last.get("output_tokens")
            res.cached_tokens = last.get("cached_input_tokens")
            res.initial_tokens = usages[0].get("input_tokens")
        res.answer = texts[-1] if texts else None
        reg: dict[str, int] = {}
        for e in events:
            it = e.get("item") or {}
            kind = it.get("item_type") or it.get("type")
            if kind == "command_execution":
                cmd = it.get("command")
                # codex reports the full argv including the shell wrapper and
                # quoting; name the first real program the command actually runs
                argv = cmd if isinstance(cmd, list) else str(cmd or "").split()
                flat = " ".join(str(a) for a in argv)
                flat = flat.replace("'", " ").replace('"', " ")
                words = [w for w in flat.split()
                         if w and not w.startswith("-")
                         and Path(w).name not in {"bash", "sh", "zsh", "-lc", "lc"}]
                # skip shell builtins that merely position the command
                while words and words[0] in {"cd", "&&", ";", "cd;"}:
                    words.pop(0)
                    while words and (words[0].startswith("/") or words[0].startswith(".")):
                        words.pop(0)
                    while words and words[0] in {"&&", ";"}:
                        words.pop(0)
                name = f"shell:{Path(words[0]).name}" if words else "shell"
                reg[name] = reg.get(name, 0) + 1
            elif kind == "collab_tool_call":
                # codex can delegate to sub-agents. Their tool calls and tokens
                # are billed to separate threads and do NOT appear in the parent's
                # usage record, so any cell that delegates is an undercount and is
                # flagged rather than compared as-is.
                tool = it.get("tool") or "collab"
                reg[f"delegate:{tool}"] = reg.get(f"delegate:{tool}", 0) + 1
                res.delegated += 1
                res.totals_incomplete = True
            elif kind == "mcp_tool_call":
                nm = it.get("tool") or it.get("name") or "mcp__unknown"
                reg[f"mcp__{nm}" if not str(nm).startswith("mcp") else str(nm)] = \
                    reg.get(f"mcp__{nm}", 0) + 1
        res.tool_register = reg
        res.tool_calls = sum(reg.values())
        return res


class QwenCodeAdapter(Adapter):
    name = "qwen-code"
    supports_mcp = True

    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        s: dict = {"tools": {"approvalMode": "yolo"}}
        if arm == "mcp":
            s["mcpServers"] = {"github": {"command": self.mcp_bin,
                                          "args": ["stdio"], "trust": True}}
        (run_dir / ".qwen").mkdir(exist_ok=True)
        (run_dir / ".qwen" / "settings.json").write_text(json.dumps(s, indent=1))
        if arm == "mcp":
            import subprocess
            subprocess.run(["qwen", "mcp", "approve", "github"], cwd=str(run_dir),
                           env=self.env(model), capture_output=True, text=True)

    def command(self, model: str, arm: str) -> list[str]:
        return ["qwen", "--prompt", prompt(), "--output-format", "json"]

    def env(self, model: str) -> dict[str, str]:
        env = super().env(model)
        base, key = endpoint_for(model)
        env["OPENAI_BASE_URL"] = base
        env["OPENAI_API_KEY"] = key or "local"
        env["OPENAI_MODEL"] = model
        return env

    def parse(self, stdout, stderr, res: RunResult) -> RunResult:
        events = json.loads(stdout)
        us = [e["usage"] for e in events
              if isinstance(e.get("usage"), dict) and e["usage"].get("total_tokens")]
        if us:
            res.initial_tokens = us[0].get("input_tokens")
            res.total_input_tokens = us[-1].get("input_tokens")
            res.total_output_tokens = us[-1].get("output_tokens")
            res.cached_tokens = us[-1].get("cache_read_input_tokens")
        result = next((e for e in events if e.get("type") == "result"), {})
        res.answer = result.get("result")
        reg: dict[str, int] = {}
        _walk_tool_calls(events, reg)
        res.tool_register = reg
        res.tool_calls = sum(reg.values())
        return res


class PiAdapter(Adapter):
    name = "pi"
    supports_mcp = False        # verified: pi 0.73.1 ships no MCP client

    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        pass

    def env(self, model: str) -> dict[str, str]:
        env = super().env(model)
        # pi prefers an inherited OPENAI_API_KEY over the key configured for its
        # provider. Passing the real key made it authenticate to the proxy with a
        # credential the proxy does not know, which LiteLLM rejects in
        # user_api_key_auth as "No connected db" — an error that reads like a
        # database problem and is actually key rejection. Drop it so pi uses the
        # provider key from models.json.
        env.pop("OPENAI_API_KEY", None)
        return env

    def command(self, model: str, arm: str) -> list[str]:
        # providers are registered by setup/configure_pi.py
        if model == "glm-5.2":
            provider, mid = "glm", model
        elif model in LOCAL_MODELS:
            provider, mid = "ollama", model
        else:
            provider, mid = "openai", model
        return ["pi", "-p", "--mode", "json", "--thinking", "off",
                "--provider", provider, "--model", mid, prompt()]

    def parse(self, stdout, stderr, res: RunResult) -> RunResult:
        events = [json.loads(l) for l in stdout.splitlines()
                  if l.strip().startswith("{")]
        turns = [e for e in events if e.get("type") == "turn_end"]
        usages = [(t.get("message") or {}).get("usage") or {} for t in turns]
        usages = [u for u in usages if u]
        if usages:
            res.initial_tokens = ((usages[0].get("input") or 0)
                                  + (usages[0].get("cacheRead") or 0))
            # pi reports fresh input and cached reads separately; the prompt the
            # model actually saw is the sum of the two
            res.total_input_tokens = sum((u.get("input") or 0) + (u.get("cacheRead") or 0)
                                         for u in usages)
            res.total_output_tokens = sum(u.get("output") or 0 for u in usages)
            res.cached_tokens = sum(u.get("cacheRead") or 0 for u in usages)
        final = next((e for e in reversed(events) if e.get("type") == "agent_end"), {})
        msgs = final.get("messages") or []
        for m in reversed(msgs):
            if m.get("role") == "assistant":
                parts = [c.get("text") for c in (m.get("content") or [])
                         if isinstance(c, dict) and c.get("type") == "text"]
                if parts:
                    res.answer = "\n".join(p for p in parts if p)
                    break
        reg: dict[str, int] = {}
        for t_ in turns:
            for tr in (t_.get("toolResults") or []):
                nm = tr.get("toolName") or tr.get("name") or "tool"
                reg[nm] = reg.get(nm, 0) + 1
                if tr.get("isError"):
                    res.tool_failures += 1
        if not reg:
            _walk_tool_calls(events, reg)
        res.tool_register = reg
        res.tool_calls = sum(reg.values())
        return res


ADAPTERS = {a.name: a for a in (ClaudeCodeAdapter, CodexAdapter,
                                QwenCodeAdapter, PiAdapter)}
