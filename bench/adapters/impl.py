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

import datetime
import json
import os
import pathlib
import subprocess
from pathlib import Path

from bench.adapters.base import Adapter, RunResult
from bench.task_e2 import prompt_for   # Experiment 2 workflow

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

# Kept only to mark which models are free; ALL traffic goes through the proxy so
# that one accounting path covers every cell. Experiment 1 mixed direct and
# proxied routing and lost the per-request record for the direct cells.
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


def _proxy_rows_since(t0: str, model: str) -> list[dict]:
    """Proxy usage rows for `model` stamped at or after `t0`.

    Some scaffoldings report no usage of their own, so the LiteLLM log is the
    only token source. The runner is strictly sequential, so a run owns every
    row for its model from its start onward and windows cannot interleave.
    """
    log = pathlib.Path(os.environ.get(
        "E1_USAGE_LOG",
        str(pathlib.Path(__file__).resolve().parents[2] / "results" / "usage.jsonl")))
    if not log.exists():
        return []
    rows = []
    for line in log.read_text().splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("model") == model and d.get("ts", "") >= t0:
            rows.append(d)
    return rows


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

    # Models Claude Code reaches on its own subscription credentials. Everything
    # else is routed through the proxy exactly like the other scaffoldings.
    #
    # The scaffolding was previously assumed to be pinned to Anthropic, and both
    # this harness and the manuscript said so. It is not: ANTHROPIC_BASE_URL
    # redirects it at any endpoint speaking the Anthropic message format, which
    # LiteLLM serves at /v1/messages. What is genuinely pinned is a SUBSCRIPTION
    # account, whose OAuth token only authenticates against Anthropic — a
    # property of the credential we chose, not of the scaffolding.
    NATIVE = {"sonnet-5", "opus-5", "fable-5"}

    # the matrix names models uniformly (sonnet-5); claude takes bare aliases
    ALIAS = {"sonnet-5": "sonnet", "opus-5": "opus", "fable-5": "fable"}

    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        self._t0 = datetime.datetime.now().isoformat()
        if arm == "mcp":
            cfg = {"mcpServers": {"github": {
                "command": self.mcp_bin, "args": ["stdio"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_PERSONAL_ACCESS_TOKEN"}}}}
            (run_dir / ".mcp.json").write_text(json.dumps(cfg, indent=1))

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = super().env(model, arm)
        if model in self.NATIVE:
            return env
        base, key = endpoint_for(model)
        # Claude Code appends /v1/messages itself, so it needs the proxy ROOT,
        # not the /v1 path handed to the OpenAI-speaking scaffoldings.
        env["ANTHROPIC_BASE_URL"] = base[:-3] if base.endswith("/v1") else base
        env["ANTHROPIC_AUTH_TOKEN"] = key
        env["ANTHROPIC_MODEL"] = model
        # An inherited key outranks the proxy token and would send the run to
        # Anthropic at full price under a local model's name.
        env.pop("ANTHROPIC_API_KEY", None)
        return env

    def command(self, model: str, arm: str) -> list[str]:
        # stream-json (not json): the plain json mode returns only the final
        # result, so tool calls would be invisible and reported as zero
        name = self.ALIAS.get(model, model) if model in self.NATIVE else model
        cmd = ["claude", "-p", prompt_for(arm), "--output-format", "stream-json",
               "--verbose", "--model", name,
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
        res.answer = doc.get("result")
        reg: dict[str, int] = {}
        _walk_tool_calls(events, reg)
        res.tool_register = reg
        res.tool_calls = sum(reg.values())

        if res.model in self.NATIVE:
            # Subscription route: no proxy in the path, so the scaffolding's own
            # record is the only source. Anthropic's convention counts cache
            # reads separately from input_tokens, so the total is their sum.
            res.total_input_tokens = (u.get("input_tokens") or 0) + \
                (u.get("cache_read_input_tokens") or 0) + \
                (u.get("cache_creation_input_tokens") or 0)
            res.total_output_tokens = u.get("output_tokens")
            res.cached_tokens = u.get("cache_read_input_tokens")
            iters = u.get("iterations") or []
            if iters:
                first = iters[0]
                res.initial_tokens = (first.get("input_tokens") or 0) + \
                    (first.get("cache_read_input_tokens") or 0) + \
                    (first.get("cache_creation_input_tokens") or 0)
            res.notes.append("tokens self-reported (subscription; no proxy in path)")
            res.notes.append(f"claude-reported billed cost ${doc.get('total_cost_usd')}")
            return res

        # Proxied route: the proxy log is the source of truth, as for every other
        # scaffolding. The top-level `usage` block reports all zeros when the
        # backend is not Anthropic — the scaffolding's own figures survive only
        # under `modelUsage`, which is recorded below as a cross-check.
        rows = _proxy_rows_since(self._t0, res.model)
        if rows:
            res.total_input_tokens = sum(r.get("prompt_tokens") or 0 for r in rows)
            res.total_output_tokens = sum(r.get("completion_tokens") or 0 for r in rows)
            cached = [r.get("cached_tokens") for r in rows
                      if r.get("cached_tokens") is not None]
            if cached:
                res.cached_tokens = sum(cached)
            res.initial_tokens = rows[0].get("prompt_tokens")
            res.notes.append(f"tokens from proxy log ({len(rows)} requests)")
        else:
            res.notes.append("no proxy rows matched — tokens unattributed")
        mu = (doc.get("modelUsage") or {}).get(res.model) or {}
        if mu:
            self_total = ((mu.get("inputTokens") or 0)
                          + (mu.get("cacheReadInputTokens") or 0)
                          + (mu.get("cacheCreationInputTokens") or 0))
            res.notes.append(
                f"scaffolding self-report cross-check: input={self_total} "
                f"output={mu.get('outputTokens')} "
                f"(proxy: input={res.total_input_tokens} "
                f"output={res.total_output_tokens})")
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
        cmd += [prompt_for(arm)]
        return cmd

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = super().env(model, arm)
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
        # web_fetch is neither surface under test. Left enabled it was the only
        # path this scaffolding ever took on the CLI arm, so the arm measured
        # HTTP fetches rather than the command line.
        s: dict = {"tools": {"approvalMode": "yolo",
                             "disabled": ["web_fetch"]}}
        if arm == "mcp":
            s["mcpServers"] = {"github": {"command": self.mcp_bin,
                                          "args": ["stdio"], "trust": True}}
        (run_dir / ".qwen").mkdir(exist_ok=True)
        (run_dir / ".qwen" / "settings.json").write_text(json.dumps(s, indent=1))
        if arm == "mcp":
            import subprocess
            subprocess.run(["qwen", "mcp", "approve", "github"], cwd=str(run_dir),
                           env=self.env(model, arm), capture_output=True, text=True)

    def command(self, model: str, arm: str) -> list[str]:
        return ["qwen", "--prompt", prompt_for(arm), "--output-format", "json"]

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = super().env(model, arm)
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

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = super().env(model, arm)
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
                "--provider", provider, "--model", mid, prompt_for(arm)]

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


TAU_SRC = str(pathlib.Path.home() / "Code/tau/src")
TAU_RUN = str(pathlib.Path.home() / "Code/mcp-vs-cli-bench/bin/tau-run")


class TauAdapter(Adapter):
    """Tau — a Python implementation of pi's design philosophy.

    Included because LAMB's agent layer is being refactored onto it, so the
    benchmark needs to cover it, and because it tests whether the minimal-
    scaffolding result transfers to a second implementation. It is not an
    independent confirmation: Tau follows pi's philosophy deliberately, so a
    matching result shows the principle is portable rather than showing that the
    catalogue is the sole cause.

    Ships no MCP client, so its catalogue arm is void by capability.
    """

    name = "tau"
    supports_mcp = False

    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        # Tau reports no usage of its own, so the proxy log is the only token
        # source. Stamp the start so parse() can claim exactly the rows this
        # run produced; the runner is sequential, so windows cannot overlap.
        self._t0 = datetime.datetime.now().isoformat()

    def command(self, model: str, arm: str) -> list[str]:
        # Two things matter here and both cost us a debugging session.
        #
        # 1. tau_coding.cli defines a typer app but has no __main__ guard, so
        #    `python -m tau_coding.cli` exits silently having done nothing.
        #    bin/tau-run invokes the app object directly.
        # 2. The prompt is a VARIADIC positional. Putting it first makes typer
        #    swallow every following flag into it — the run then launches the
        #    interactive TUI with a prompt reading "<task> --print --mode json
        #    …" and blocks forever. Flags first, `--`, prompt last.
        #
        # The provider is registered in ~/.tau/catalog.toml (see setup/), which
        # points at the LiteLLM proxy, so --base-url is neither needed nor
        # accepted here: on this path it configures `tau setup`, not the run.
        return [TAU_RUN, "--print", "--mode", "json",
                "--provider", "bench", "--model", model,
                "--cwd", ".", "--", prompt_for(arm)]

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = super().env(model, arm)
        env["PYTHONPATH"] = TAU_SRC
        env["BENCH_KEY"] = PROXY_KEY
        env["OPENAI_API_KEY"] = PROXY_KEY
        env["OPENAI_BASE_URL"] = PROXY_BASE
        return env

    def parse(self, stdout, stderr, res: RunResult) -> RunResult:
        events = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        # Tau speaks its own event dialect: {"type": "tool_execution_start",
        # "toolName": "bash", ...}. The shared walker keys off type ==
        # "tool_use"/"function_call" with a "name" field, so it silently
        # records zero calls here — a wrong number, not a missing one.
        reg: dict[str, int] = {}
        for e in events:
            if e.get("type") == "tool_execution_start" and e.get("toolName"):
                nm = e["toolName"]
                reg[nm] = reg.get(nm, 0) + 1
        res.tool_register = reg
        res.tool_calls = sum(reg.values())
        texts = [e.get("text") or e.get("content") for e in events
                 if isinstance(e.get("text") or e.get("content"), str)]
        res.answer = texts[-1] if texts else stdout[-2000:]
        # Tau emits no usage record, so the proxy log is the sole token source.
        # Claim the rows for this model stamped at or after the run started.
        log = pathlib.Path(os.environ.get(
            "E1_USAGE_LOG", str(pathlib.Path(__file__).resolve().parents[2]
                                / "results" / "usage.jsonl")))
        rows = []
        if log.exists():
            for line in log.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("model") == res.model and d.get("ts", "") >= self._t0:
                    rows.append(d)
        if rows:
            res.total_input_tokens = sum(r.get("prompt_tokens") or 0 for r in rows)
            res.total_output_tokens = sum(r.get("completion_tokens") or 0 for r in rows)
            # Absent is not zero: only claim a cache figure if the provider
            # actually reported one, otherwise the hit rate reads as a real 0%.
            cached = [r.get("cached_tokens") for r in rows
                      if r.get("cached_tokens") is not None]
            if cached:
                res.cached_tokens = sum(cached)
            res.notes.append(f"tokens from proxy log ({len(rows)} requests)")
        else:
            res.notes.append("no proxy rows matched — tokens unattributed")
        return res


ADAPTERS["tau"] = TauAdapter


HERMES_BIN = str(pathlib.Path.home() / "Code/hermes/.venv-bench/bin/hermes")


class HermesAdapter(Adapter):
    """Hermes — NousResearch's agent, and the fourth MCP-capable scaffolding.

    It matters because the comparison rests on that side of the matrix: before
    Hermes it held three MCP-capable harnesses against two controls, and one of
    the three runs a single model.

    It is also the far end of the design axis from pi and Tau. Hermes enables
    roughly thirteen toolsets by default — web, browser, terminal, file, code
    execution, vision, image generation, TTS, skills, todo, memory, session
    search, clarify. That is the shipped default, not a configuration chosen to
    make it look expensive.
    """

    name = "hermes"
    supports_mcp = True

    # CLI arm: the shell and files, nothing else. MCP arm: the catalogue,
    # without a terminal to fall back on.
    # -t gates MCP tools as well as built-ins, so naming only built-in
    # toolsets on the MCP arm excluded the catalogue that had just been
    # attached and verified. The server was enabled and absent from the
    # request at the same time; `hermes mcp list` confirms attachment, not
    # exposure. The arm must name the server itself.
    TOOLSETS = {"cli": "terminal,file", "mcp": "file,github"}

    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        self._t0 = datetime.datetime.now().isoformat()
        self._usage = run_dir / "hermes-usage.json"
        # Register or remove the catalogue per arm so the surface is set by
        # configuration rather than by asking the agent to behave.
        # `hermes mcp add` is interactive on BOTH paths: it prompts "Save config
        # anyway?" when the connection fails and "Enable all N tools?" when it
        # succeeds. With no stdin it takes the default and, on the failure path,
        # saves nothing — while still exiting 0. The first Hermes matrix ran
        # four "MCP" cells with no server attached and no error anywhere,
        # because a setup step that fails loudly to a human failed silently to
        # a script. Feed it "y" and then VERIFY, rather than trusting an exit
        # code that does not distinguish the two outcomes.
        subprocess.run([HERMES_BIN, "mcp", "remove", "github"],
                       input="y\n", capture_output=True, text=True, timeout=120)
        if arm == "mcp":
            subprocess.run(
                [HERMES_BIN, "mcp", "add", "github", "--command", self.mcp_bin,
                 "--env", f"GITHUB_PERSONAL_ACCESS_TOKEN={self.gh_token}",
                 "--args", "stdio"],
                input="y\n" * 4, capture_output=True, text=True, timeout=600)
        listing = subprocess.run([HERMES_BIN, "mcp", "list"], capture_output=True,
                                 text=True, timeout=120).stdout
        attached = "github" in listing and "enabled" in listing
        if arm == "mcp" and not attached:
            raise RuntimeError(
                "github MCP server not attached — refusing to run an MCP arm "
                "with no catalogue (this silently produced four invalid cells)")
        if arm == "cli" and attached:
            raise RuntimeError(
                "github MCP server still attached on the CLI arm — the arms "
                "would not be isolated")

    def command(self, model: str, arm: str) -> list[str]:
        # --provider must accompany -m. Alone, -m resolves the model against
        # the provider registry, misses (the endpoint is a custom one), and
        # fails with "No LLM provider configured" — which reads as though no
        # provider were set up at all, when in fact config.yaml holds a valid
        # one and the bare invocation works.
        return [HERMES_BIN, "-z", prompt_for(arm),
                "--usage-file", str(self._usage),
                "-t", self.TOOLSETS[arm],
                "--provider", "custom", "-m", model,
                "--reasoning", "none"]

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = super().env(model, arm)
        # model.key_env is accepted by `hermes config set` and then resolves to
        # nothing at request time, surfacing as LiteLLM's "No connected db" —
        # key rejection wearing a database error's clothes. The key is set
        # directly via model.api_key; drop inherited keys so nothing competes.
        env.pop("OPENAI_API_KEY", None)
        env["BENCH_KEY"] = PROXY_KEY
        return env

    def parse(self, stdout, stderr, res: RunResult) -> RunResult:
        reg: dict[str, int] = {}
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    _walk_tool_calls(json.loads(line), reg)
                except json.JSONDecodeError:
                    pass
        # Hermes writes its own usage report, which no other scaffolding does.
        # It is recorded as a cross-check; the proxy stays the source of truth.
        if self._usage.exists():
            try:
                u = json.loads(self._usage.read_text())
                res.notes.append(f"hermes self-reported usage: {json.dumps(u)[:200]}")
                for k in ("tool_calls", "tools", "tool_counts"):
                    if isinstance(u.get(k), dict):
                        for nm, n in u[k].items():
                            reg[nm] = reg.get(nm, 0) + int(n)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        res.tool_register = reg
        res.tool_calls = sum(reg.values())
        res.answer = stdout[-2000:]
        rows = _proxy_rows_since(self._t0, res.model)
        if rows:
            res.total_input_tokens = sum(r.get("prompt_tokens") or 0 for r in rows)
            res.total_output_tokens = sum(r.get("completion_tokens") or 0 for r in rows)
            cached = [r.get("cached_tokens") for r in rows
                      if r.get("cached_tokens") is not None]
            if cached:
                res.cached_tokens = sum(cached)
            res.notes.append(f"tokens from proxy log ({len(rows)} requests)")
        else:
            res.notes.append("no proxy rows matched — tokens unattributed")
        return res


ADAPTERS["hermes"] = HermesAdapter
