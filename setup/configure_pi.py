#!/usr/bin/env python3
"""Register the benchmark's model providers with pi.

pi takes custom providers through ~/.pi/agent/models.json rather than
environment variables, and ships knowing only what has already been added. The
benchmark needs three: the local GLM served by llama-server, the Ollama host,
and OpenRouter for the hosted models.

Idempotent — merges into whatever is already there rather than overwriting, so
running it does not clobber a provider configured for other work.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

MODELS_JSON = pathlib.Path.home() / ".pi" / "agent" / "models.json"

FREE = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}


def model(mid: str, name: str, ctx: int, cost: dict | None = None) -> dict:
    return {"id": mid, "name": name, "reasoning": False, "input": ["text"],
            "cost": cost or FREE, "contextWindow": ctx, "maxTokens": 8192}


PROVIDERS = {
    "glm": {
        "name": "GLM-5.2 local (llama-server)",
        "baseUrl": "http://localhost:4000/v1",
        "api": "openai-completions", "apiKey": "sk-e1-local",
        "models": [model("glm-5.2", "GLM-5.2 (local)", 131072)],
    },
    "ollama": {
        "name": "Ollama (studio64)",
        "baseUrl": "http://localhost:4000/v1",
        "api": "openai-completions", "apiKey": "sk-e1-local",
        "models": [model("qwen3.5:122b", "Qwen3.5 122B (local)", 131072),
                   model("qwen3.6:27b", "Qwen3.6 27B (local)", 262144)],
    },
    "openai": {
        "name": "OpenAI",
        "baseUrl": "http://localhost:4000/v1",
        "api": "openai-completions",
        "apiKey": "sk-e1-local",
        "models": [
            model("gpt-5.6-sol", "GPT-5.6 Sol", 400_000,
                  {"input": 5.0, "output": 30.0, "cacheRead": 0, "cacheWrite": 0}),
            model("gpt-5.6-luna", "GPT-5.6 Luna", 400_000,
                  {"input": 0.1, "output": 0.6, "cacheRead": 0, "cacheWrite": 0}),
            model("gpt-5.6-terra", "GPT-5.6 Terra", 400_000,
                  {"input": 1.0, "output": 6.0, "cacheRead": 0, "cacheWrite": 0}),
        ],
    },
}


def main() -> None:
    MODELS_JSON.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if MODELS_JSON.exists():
        try:
            current = json.loads(MODELS_JSON.read_text())
        except json.JSONDecodeError:
            print("existing models.json is not valid JSON; refusing to overwrite",
                  file=sys.stderr)
            raise SystemExit(1)

    providers = current.setdefault("providers", {})
    if not PROVIDERS["openai"]["apiKey"]:
        print("warning: OPENAI_API_KEY unset — hosted pi cells will fail",
              file=sys.stderr)
    for key, spec in PROVIDERS.items():
        providers[key] = spec          # last writer wins, by design
    MODELS_JSON.write_text(json.dumps(current, indent=2))
    print(f"configured providers in {MODELS_JSON}: {', '.join(PROVIDERS)}")


if __name__ == "__main__":
    main()
