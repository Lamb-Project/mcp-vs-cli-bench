#!/usr/bin/env python3
"""Seed and reset the Experiment 2 private fixture.

The task creates branches, opens pull requests, comments and merges, so the
repository accumulates state. This script tears that state down and rebuilds it,
so every run starts from an identical position and a run cannot be helped or
hindered by what a previous one left behind.

Idempotent by construction: it deletes what it is about to create.

Credential: the scoped PAT from the keychain, never a literal.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

REPO = "Lamb-Project/aawd-e2-fixture"
BASE = "main"
BUG_LABEL = "bug"
TERM = "tokenise"          # the term the task searches for


def token() -> str:
    r = subprocess.run(["security", "find-generic-password", "-a", "mcp-bench",
                        "-s", "mcp-bench-e2-token", "-w"],
                       capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        sys.exit("no fixture token in keychain (mcp-bench / mcp-bench-e2-token)")
    return r.stdout.strip()


def api(path: str, method="GET", body=None, tok=None, ok_codes=(0,)):
    ep = f"repos/{REPO}" if not path else f"repos/{REPO}/{path}"
    cmd = ["gh", "api", ep]
    if method != "GET":
        cmd += ["-X", method]
    if body is not None:
        cmd += ["--input", "-"]
    env = {"GH_TOKEN": tok} if tok else None
    import os
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                       capture_output=True, text=True, env=e)
    if r.returncode and r.returncode not in ok_codes:
        return None, r.stderr.strip()[:200]
    try:
        return json.loads(r.stdout or "null"), None
    except json.JSONDecodeError:
        return r.stdout, None


# --- content the task acts on -------------------------------------------------

BROKEN = '''"""Tokenise a line of text. Deliberately broken: see issue."""


def tokenise(line: str) -> list[str]:
    # BUG: splits on every character instead of on whitespace
    return list(line)


if __name__ == "__main__":
    print(tokenise("the quick brown fox"))
'''

FIXED = '''"""Tokenise a line of text."""


def tokenise(line: str) -> list[str]:
    return line.split()


if __name__ == "__main__":
    print(tokenise("the quick brown fox"))
'''

README = """# aawd-e2-fixture

Private fixture for **Experiment 2** of the MCP-versus-CLI benchmark.

Issues and pull requests here are synthetic. They are created by a seeding script
before each measurement run and torn down afterwards. Nothing here describes a
real defect and no one is expected to act on it.

State is disposable and reset between runs; do not build on it.
"""

FILES = {
    "README.md": README,
    "src/tokenise.py": BROKEN,
    "src/__init__.py": "",
    "patches/fix-tokenise.py": FIXED,       # pre-authored: the agent applies this
    "docs/notes.md": "Scratch notes.\n",
}


def put_file(tok, path, content, message, branch=BASE):
    cur, _ = api(f"contents/{path}?ref={branch}", tok=tok)
    body = {"message": message, "branch": branch,
            "content": base64.b64encode(content.encode()).decode()}
    if isinstance(cur, dict) and cur.get("sha"):
        body["sha"] = cur["sha"]
    _, err = api(f"contents/{path}", "PUT", body, tok)
    return err


def reset(tok):
    """Remove everything a previous run may have created."""
    # branches other than main
    brs, _ = api("branches", tok=tok)
    for b in (brs or []):
        if b.get("name") != BASE:
            api(f"git/refs/heads/{b['name']}", "DELETE", tok=tok)
    # open PRs
    prs, _ = api("pulls?state=open", tok=tok)
    for p in (prs or []):
        api(f"pulls/{p['number']}", "PATCH", {"state": "closed"}, tok)
    # issues (close, cannot delete via API)
    iss, _ = api("issues?state=open", tok=tok)
    for i in (iss or []):
        if not i.get("pull_request"):
            api(f"issues/{i['number']}", "PATCH", {"state": "closed"}, tok)
    print("  reset: branches, PRs and issues cleared")


def seed(tok):
    for path, content in FILES.items():
        err = put_file(tok, path, content, f"seed: {path}")
        if err:
            print(f"  ! {path}: {err}")
    print(f"  seeded {len(FILES)} files")

    api("labels", "POST", {"name": BUG_LABEL, "color": "d73a4a",
                           "description": "synthetic"}, tok)

    issue, err = api("issues", "POST", {
        "title": f"tokenise() splits on characters instead of whitespace",
        "body": (f"`src/tokenise.py` returns one element per character.\n\n"
                 f"Expected `{TERM}` of `the quick brown fox` to give four "
                 f"tokens; it gives nineteen.\n\n"
                 f"A corrected implementation is in `patches/fix-tokenise.py`."),
        "labels": [BUG_LABEL]}, tok)
    if err:
        print("  ! issue:", err)
    else:
        print(f"  seeded issue #{issue['number']} labelled {BUG_LABEL}")

    # decoys, so "find the issue labelled bug mentioning X" needs a real search
    for t in ("Update docs/notes.md wording",
              "Consider adding type hints to src/"):
        api("issues", "POST", {"title": t, "body": "Synthetic decoy."}, tok)
    print("  seeded 2 decoy issues")
    return issue


def main():
    tok = token()
    meta, err = api("", tok=tok)
    if err:
        sys.exit(f"cannot reach {REPO}: {err}")
    print(f"fixture {REPO} (private={meta.get('private')})")
    if "--reset-only" not in sys.argv:
        # main must exist before anything else can be written
        if not meta.get("size"):
            put_file(tok, "README.md", README, "seed: initial commit")
    reset(tok)
    if "--reset-only" in sys.argv:
        return
    issue = seed(tok)
    tags, _ = api("tags", tok=tok)
    print(f"  ground truth: issue #{issue['number'] if issue else '?'}, "
          f"{len(FILES)} files, {len(tags or [])} tags")


if __name__ == "__main__":
    main()
