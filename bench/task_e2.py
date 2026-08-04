"""Experiment 2 task: a write workflow on the private fixture.

Roughly double Experiment 1's operation count (10-14 tool calls against 5-6), and
it writes, because a read-only task lets an agent substitute one bulk fetch for
several targeted calls — which is exactly what happened in Experiment 1.

The reporting rule this task exists to serve: **a token ratio is only meaningful
when both arms completed the task and both used only their assigned surface.**
A ratio below 1 is not a finding that MCP is cheaper; in every Experiment 1 case
it was either an incomplete run burning tokens on flailing, or an arm that was
not the arm it claimed to be.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

REPO = "Lamb-Project/aawd-e2-fixture"
BUG_ISSUE = 21   # discovered from the live fixture
BRANCH_HINT = "fix-tokenise"
PR_PHRASE = "needs a test"
MERGE_TARGET = "main"


@dataclass(frozen=True)
class Check:
    key: str
    describe: str
    verify: Callable[[dict], bool]   # takes repo state gathered after the run


def _has(state: dict, path: str, default=None):
    cur = state
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


# Scored against repository state read back through the API after the run,
# never against the agent's own claims.
CHECKS: tuple[Check, ...] = (
    Check("branch_created",
          "a branch was created from main",
          lambda s: any(BRANCH_HINT in b or str(BUG_ISSUE) in b
                        for b in s.get("branches", []))),
    Check("patch_applied",
          "src/tokenise.py now splits on whitespace",
          lambda s: "line.split()" in (s.get("tokenise_src") or "")),
    Check("pr_opened",
          "a pull request was opened against main",
          lambda s: bool(s.get("prs"))),
    Check("pr_links_issue",
          f"the PR body references issue #{BUG_ISSUE}",
          lambda s: any(f"#{BUG_ISSUE}" in (p.get("body") or "")
                        for p in s.get("prs", []))),
    Check("reported_file_count",
          "the answer reports the file count under src/",
          lambda s: bool(re.search(r"(?<!\d)2(?!\d)", s.get("answer") or ""))),
)

ARM_PREAMBLE = {
    "cli": ("You have the authenticated GitHub CLI (`gh`) and `git` available in "
            "your shell. Use them for every GitHub operation. The repository is "
            "private; anonymous HTTP requests to it will fail."),
    "mcp": ("You have GitHub tools available through an attached MCP server. Use "
            "them for every GitHub operation. The repository is private and your "
            "shell has no GitHub credentials, so `gh` and `curl` will fail."),
    # kept identical in length and specificity so neither arm is better briefed
}

# Experiment 3 sizing. Experiment 2 asked for ten operations including review and
# merge; every run died at or before the review step, completion never exceeded
# 20%, and one agent made 118 tool calls without finishing. Tokens spent flailing
# are not a measurement of a surface's cost, so the task is cut back to the six
# operations that precede the failure point — roughly double Experiment 1,
# without crossing into the range where completion collapses.
BODY = f"""Working in the private GitHub repository {REPO}, carry out this \
workflow. Do the steps in order.

1. Find the open issue labelled `bug` that concerns tokenising text. Note its number.
2. Create a branch off `main` named `{BRANCH_HINT}`.
3. Read the corrected implementation at `patches/fix-tokenise.py`.
4. On your branch, replace the contents of `src/tokenise.py` with that corrected
   implementation, and commit the change.
5. Open a pull request from your branch into `main`, with a body that references
   the issue number.
6. Report how many files are in the `src/` directory.

When you are done, output the issue number, the pull request number and the file \
count, and nothing else. Do not review or merge the pull request."""


def prompt_for(arm: str) -> str:
    return ARM_PREAMBLE.get(arm, "") + "\n\n" + BODY


def score(state: dict) -> tuple[float, dict[str, bool]]:
    """Percentage of the workflow genuinely completed, verified against the API."""
    results = {c.key: bool(c.verify(state)) for c in CHECKS}
    pct = round(100.0 * sum(results.values()) / len(CHECKS), 1)
    return pct, results
