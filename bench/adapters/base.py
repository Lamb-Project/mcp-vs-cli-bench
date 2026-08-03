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
    notes: list[str] = field(default_factory=list)

    def finalise(self) -> "RunResult":
        if self.tool_calls:
            self.tool_success_ratio = round(
                (self.tool_calls - self.tool_failures) / self.tool_calls, 3)
        if self.total_input_tokens and self.cached_tokens is not None:
            self.cache_hit_pct = round(
                100.0 * self.cached_tokens / max(1, self.total_input_tokens), 1)
        if self.answer is not None:
            s = score(self.answer)
            self.rubric = s.items
            self.completion_pct = s.pct
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
    def env(self, model: str) -> dict[str, str]:
        env = dict(os.environ)
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = self.gh_token
        return env

    def run(self, model: str, arm: str, timeout: int = 3600) -> RunResult:
        res = RunResult(scaffolding=self.name, model=model, arm=arm)
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
                                  env=self.env(model), capture_output=True,
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


def mcp_server_spec(mcp_bin: str, token: str) -> dict:
    """Shared stdio MCP server definition.

    The token is passed through the process environment by every adapter rather
    than written here, because several scaffoldings persist their config to disk
    and a credential in a committed config file is how secrets leak.
    """
    return {"command": mcp_bin, "args": ["stdio"], "trust": True}


def prompt() -> str:
    return PROMPT
