#!/usr/bin/env python3
"""Read repository state back through the API and score a run against it.

Scoring from the agent's own answer would credit a claim; this credits an
outcome. Experiment 2 showed why that matters — agents reported success for
workflows they had not performed.
"""
from __future__ import annotations

import json
import os
import subprocess

from bench.task_e2 import REPO, score


def _tok() -> str:
    return subprocess.run(["security", "find-generic-password", "-a", "mcp-bench",
                           "-s", "mcp-bench-e2-token", "-w"],
                          capture_output=True, text=True).stdout.strip()


def _api(path, tok):
    e = dict(os.environ); e["GH_TOKEN"] = tok
    r = subprocess.run(["gh", "api", f"repos/{REPO}/{path}"],
                       capture_output=True, text=True, env=e)
    try:
        return json.loads(r.stdout or "null")
    except json.JSONDecodeError:
        return None


def gather(answer: str) -> dict:
    tok = _tok()
    brs = _api("branches", tok) or []
    prs = _api("pulls?state=all", tok) or []
    src = ""
    for b in brs:
        c = _api(f"contents/src/tokenise.py?ref={b.get('name')}", tok)
        if isinstance(c, dict) and c.get("content"):
            import base64
            body = base64.b64decode(c["content"]).decode(errors="replace")
            if "line.split()" in body:
                src = body
                break
    files = _api("contents/src", tok) or []
    return {"branches": [b.get("name") for b in brs],
            "prs": [{"body": p.get("body"), "merged": bool(p.get("merged_at"))}
                    for p in prs],
            "tokenise_src": src,
            "src_files": len(files) if isinstance(files, list) else 0,
            "answer": answer or ""}


def verify(answer: str):
    return score(gather(answer))
