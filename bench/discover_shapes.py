#!/usr/bin/env python3
"""Discover each scaffolding's headless telemetry shape before writing parsers.

Four scaffoldings, four different JSON dialects, and only qwen-code's is known.
Writing parsers against guesses would burn paid runs to find out they were
wrong, so this runs one trivial prompt per scaffolding on a free model and
reports what fields actually come back — specifically where usage, cache and
tool-call information live, if they exist at all.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "results" / "shapes"
PROMPT = "Reply with exactly: OK"

GLM = {"base": "http://localhost:8000/v1", "key": "local", "model": "glm-5.2"}

CASES = {
    # scaffolding -> (argv, extra env, settings writer)
    "claude": (["claude", "-p", PROMPT, "--output-format", "json",
                "--model", "sonnet"], {}, None),
    "codex":  (["codex", "exec", "--json", "--skip-git-repo-check",
                "-c", f'model_provider="local"',
                "-c", f'model_providers.local.name="local"',
                "-c", f'model_providers.local.base_url="{GLM["base"]}"',
                "-c", 'model_providers.local.env_key="LOCAL_KEY"',
                "-m", GLM["model"],
                "--dangerously-bypass-approvals-and-sandbox", PROMPT],
               {"LOCAL_KEY": GLM["key"]}, None),
    "pi":     (["pi", "-p", "--mode", "json", "--provider", "glm",
                "--model", "glm-5.2", PROMPT], {}, None),
    "qwen":   (["qwen", "--prompt", PROMPT, "--output-format", "json"],
               {"OPENAI_API_KEY": GLM["key"], "OPENAI_BASE_URL": GLM["base"],
                "OPENAI_MODEL": GLM["model"]}, {"tools": {"approvalMode": "yolo"}}),
}


def walk_keys(obj, prefix="", found=None, depth=0):
    """Collect dotted paths whose leaf name looks like telemetry."""
    if found is None:
        found = {}
    if depth > 6:
        return found
    interesting = ("token", "usage", "cache", "cost", "tool", "duration", "turn")
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            if any(w in k.lower() for w in interesting) and not isinstance(v, (dict, list)):
                found[p] = v
            walk_keys(v, p, found, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:8]:
            walk_keys(v, f"{prefix}[]", found, depth + 1)
    return found


def run(name):
    argv, extra_env, settings = CASES[name]
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    if settings is not None:
        (d / ".qwen").mkdir()
        (d / ".qwen" / "settings.json").write_text(json.dumps(settings))

    env = dict(os.environ)
    env.update(extra_env)
    t0 = time.time()
    try:
        proc = subprocess.run(argv, cwd=str(d), env=env, capture_output=True,
                              text=True, timeout=900)
    except subprocess.TimeoutExpired:
        print(f"\n### {name}: TIMEOUT")
        return
    except FileNotFoundError:
        print(f"\n### {name}: NOT INSTALLED")
        return
    wall = round(time.time() - t0, 1)
    (d / "stdout.txt").write_text(proc.stdout)
    (d / "stderr.txt").write_text(proc.stderr)

    print(f"\n### {name}  exit={proc.returncode} wall={wall}s "
          f"stdout={len(proc.stdout)}B stderr={len(proc.stderr)}B")
    if proc.returncode != 0:
        print("  stderr tail:", proc.stderr.strip()[-400:].replace("\n", " | "))

    text = proc.stdout.strip()
    if not text:
        print("  (no stdout)")
        return

    # JSONL or single JSON?
    events = []
    try:
        parsed = json.loads(text)
        events = parsed if isinstance(parsed, list) else [parsed]
        print("  format: single JSON document")
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        print(f"  format: JSONL ({len(events)} parsed events)")

    types = {}
    for e in events:
        if isinstance(e, dict):
            t = e.get("type") or e.get("msg", {}).get("type") if isinstance(e.get("msg"), dict) else e.get("type")
            types[str(t)] = types.get(str(t), 0) + 1
    print("  event types:", json.dumps(types))

    fields = walk_keys(events)
    if fields:
        print("  telemetry-ish fields:")
        for k, v in sorted(fields.items())[:28]:
            print(f"    {k} = {v!r}"[:150])
    else:
        print("  NO telemetry fields found")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for n in (sys.argv[1:] or list(CASES)):
        run(n)
