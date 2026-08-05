# Hermes — integration notes

`NousResearch/hermes-agent`, Python, MCP-capable. Added as a **fourth
MCP-capable scaffolding**, which matters because the comparison the paper makes
rests on that side of the matrix: before Hermes it held three MCP-capable
harnesses against two controls, and one of the three (claude-code) runs only a
single model.

## Install

Not via the upstream `curl | bash` installer — that pulls uv, a Python runtime,
Node, ffmpeg and a portable Git into the user's machine. An isolated venv gets
the same CLI:

    git clone --depth 1 https://github.com/NousResearch/hermes-agent.git ~/Code/hermes
    cd ~/Code/hermes
    uv venv --python 3.12 .venv-bench
    uv pip install --python .venv-bench/bin/python -e .

Requires Python >=3.11,<3.14. The repo is ~214MB.

## Pointing it at the LiteLLM proxy

`hermes model` is interactive and will hang unattended. `hermes config set` is
not, so configure directly:

    hermes config set model.provider custom
    hermes config set model.base_url http://localhost:4000/v1
    hermes config set model.api_key  sk-e1-local
    hermes config set model.name     gpt-5.6-luna

**Use `model.api_key`, not `model.key_env`.** The `key_env` indirection is
accepted by `config set` and then resolves to nothing at request time — even
with the variable exported and written to `~/.hermes/.env`. The symptom is
`HTTP 400: No connected db.`, which is LiteLLM failing to resolve a key that is
not the master key. It reads as a proxy database problem and is actually an
auth problem; it has now cost this project time twice, once on pi and once
here.

## Arms

Built-in toolsets use plain names; MCP tools use `server:tool`. Select per
invocation with `-t/--toolsets`.

    CLI arm:  -t terminal,file
    MCP arm:  the github MCP server, without terminal

Note for the paper: Hermes enables roughly thirteen toolsets by default — web,
browser, terminal, file, code_execution, vision, image_gen, bfl, tts, skills,
todo, memory, session_search, clarify. That is the opposite end of the design
axis from pi and Tau, and it is the default, not a configuration we chose.

## Run shape

    hermes -z "<prompt>" --usage-file <path> -t <toolsets> -m <model> --reasoning none

`-z/--oneshot` prints only the final answer. `--usage-file` writes Hermes' own
JSON usage report — no other scaffolding in the study offers this, so it is a
useful cross-check, but the proxy log stays the source of truth for tokens.
