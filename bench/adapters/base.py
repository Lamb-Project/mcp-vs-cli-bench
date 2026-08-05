"""Common shape for scaffolding adapters.

Each scaffolding reports telemetry in its own format and none of them report the
same set of fields. The adapter's job is to normalise whatever is available into
one record, and — importantly — to say plainly when a field is *not available*
rather than substituting a zero. A missing cache figure and a genuine zero mean
opposite things, and conflating them would quietly corrupt the cache column.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bench.task import PROMPT, score


@dataclass
class RunResult:
    scaffolding: str
    model: str
    arm: str                      # "mcp" | "cli"

    # status
    void: bool = False
    void_reason: str | None = None
    error: str | None = None

    # the dimensions
    initial_tokens: int | None = None      # turn-1 / first-request prompt tokens
    total_input_tokens: int | None = None
    total_output_tokens: int | None = None
    cached_tokens: int | None = None
    cache_hit_pct: float | None = None
    tool_calls: int = 0
    tool_register: dict[str, int] = field(default_factory=dict)
    tool_failures: int = 0
    tool_success_ratio: float | None = None
    completion_pct: float | None = None
    rubric: dict[str, bool] = field(default_factory=dict)
    wall_s: float | None = None
    theoretical_cost_usd: float | None = None

    # provenance
    answer: str | None = None
    mcp_attached: bool | None = None      # server registered and enabled
    mcp_tools_used: int = 0               # MCP tool calls the agent actually made
    delegated: int = 0                    # sub-agents spawned; see below
    totals_incomplete: bool = False       # sub-agent cost not in the parent's usage
    notes: list[str] = field(default_factory=list)

    def assert_mcp(self, prefixes: tuple[str, ...] = ("mcp__", "mcp_")) -> None:
        """An MCP arm that never called an MCP tool did not run the arm.

        Both qwen-code (unapproved server) and codex (config override ignored)
        have silently started with no MCP tools and produced clean-looking
        numbers, so this is checked rather than assumed.
        """
        if self.arm != "mcp":
            return
        self.mcp_tools_used = sum(n for name, n in self.tool_register.items()
                                  if name.startswith(prefixes))
        if self.mcp_tools_used == 0:
            # Not void. Per the benchmark's design the MCP arm is the default
            # scaffolding *plus* an MCP server, so the shell remains available and
            # the agent chooses. Zero MCP calls means it preferred the shell —
            # which is a result about tool selection, not a broken cell. Only a
            # scaffolding with no MCP client at all is void.
            self.notes.append("MCP server attached but the agent used no MCP tool; "
                              "it completed the task through the shell")

    def finalise(self) -> "RunResult":
        if self.tool_calls:
            self.tool_success_ratio = round(
                (self.tool_calls - self.tool_failures) / self.tool_calls, 3)
        if self.total_input_tokens and self.cached_tokens is not None:
            self.cache_hit_pct = round(
                100.0 * self.cached_tokens / max(1, self.total_input_tokens), 1)
        if self.answer is not None:
            # Score against repository state read back through the API, never
            # against the agent's claim. Experiment 2 produced runs that reported
            # success for workflows they had not performed.
            try:
                from bench.verify_e2 import verify
                pct, items = verify(self.answer)
                self.completion_pct, self.rubric = pct, items
            except Exception:
                s = score(self.answer)
                self.rubric, self.completion_pct = s.items, s.pct
        return self

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class Adapter:
    name: str = "base"
    supports_mcp: bool = True

    def __init__(self, workdir: Path, mcp_bin: str, gh_token: str):
        self.workdir = workdir
        self.mcp_bin = mcp_bin
        self.gh_token = gh_token

    # --- to implement per scaffolding -------------------------------------
    def prepare(self, run_dir: Path, model: str, arm: str) -> None:
        raise NotImplementedError

    def command(self, model: str, arm: str) -> list[str]:
        raise NotImplementedError

    def parse(self, stdout: str, stderr: str, result: RunResult) -> RunResult:
        raise NotImplementedError

    # --- shared -----------------------------------------------------------
    # Experiment 2 isolation. In Experiment 1 an agent that ignored its assigned
    # surface still succeeded, so contamination was silent. Now each arm can
    # reach the fixture by exactly one route and the other route fails visibly.
    isolate_arms: bool = True

    def env(self, model: str, arm: str = "cli") -> dict[str, str]:
        env = dict(os.environ)
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = self.gh_token
        if not self.isolate_arms:
            return env
        if arm == "mcp":
            # The MCP server gets the credential through its own environment.
            # The agent's shell does not: gh is pointed at an empty config
            # directory with no token, so reaching for `gh` returns an auth
            # error instead of quietly completing the task.
            blank = self.workdir / "_no_gh_auth"
            blank.mkdir(parents=True, exist_ok=True)
            env["GH_CONFIG_DIR"] = str(blank)
            for k in ("GH_TOKEN", "GITHUB_TOKEN"):
                env.pop(k, None)
        else:
            # CLI arm: normal gh auth via the user keychain, and no MCP server
            # is configured, so the registry tokens are not paid either.
            env.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
        return env

    def unsupported(self, model: str) -> str | None:
        """Reason this scaffolding cannot reach this model at all, if any."""
        return None

    def run(self, model: str, arm: str, timeout: int = 3600) -> RunResult:
        res = RunResult(scaffolding=self.name, model=model, arm=arm)
        why = self.unsupported(model)
        if why:
            res.void = True
            res.void_reason = why
            return res
        if arm == "mcp" and not self.supports_mcp:
            res.void = True
            res.void_reason = f"{self.name} ships no MCP client"
            return res

        run_dir = self.workdir / f"{self.name}__{model.replace(':', '-')}__{arm}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True)

        try:
            self.prepare(run_dir, model, arm)
        except Exception as exc:  # noqa: BLE001
            res.void = True
            res.void_reason = f"prepare failed: {exc}"
            return res

        t0 = time.time()
        try:
            proc = subprocess.run(self.command(model, arm), cwd=str(run_dir),
                                  env=self.env(model, arm), capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            res.error = f"timeout after {timeout}s"
            res.wall_s = round(time.time() - t0, 1)
            return res.finalise()
        res.wall_s = round(time.time() - t0, 1)

        (run_dir / "stdout.txt").write_text(proc.stdout)
        (run_dir / "stderr.txt").write_text(proc.stderr)

        try:
            res = self.parse(proc.stdout, proc.stderr, res)
        except Exception as exc:  # noqa: BLE001
            res.error = f"parse failed: {exc}"
            return res.finalise()
        res.assert_mcp()
        # GLM specifically spirals when thinking is on, emitting tokens unrelated
        # to tool use and inflating whichever arm it lands in. The server sets
        # --reasoning off, but a per-request override could defeat that, so GLM
        # runs are checked rather than assumed.
        #
        # Scoped to GLM deliberately. Other models reason legitimately, and this
        # guard reads what the SCAFFOLDING PRINTS, not what the model generated —
        # a harness that reasons but does not surface it looks clean while one
        # that echoes its reasoning looks contaminated. Applied broadly it voided
        # completed runs on the two minimal harnesses and left the verbose ones
        # standing, which is exactly backwards.
        import re as _re
        if model.startswith("glm") and _re.search(r"reasoning_content|<think>",
                                                  proc.stdout):
            res.error = "reasoning output present — thinking was ON; run is void"
            res.void = True
            res.void_reason = res.error
        elif _re.search(r"reasoning_content|<think>", proc.stdout):
            # Recorded, not voided: the tokens are real and the task was really
            # done, but the total includes reasoning and is not directly
            # comparable to a harness that does not print its thinking.
            res.notes.append("reasoning output present — totals include thinking tokens")
        return res.finalise()


def mcp_server_spec(mcp_bin: str, token: str) -> dict:
    """Shared stdio MCP server definition.

    The token is passed through the process environment by every adapter rather
    than written here, because several scaffoldings persist their config to disk
    and a credential in a committed config file is how secrets leak.
    """
    return {"command": mcp_bin, "args": ["stdio"], "trust": True}


def prompt() -> str:
    return PROMPT
