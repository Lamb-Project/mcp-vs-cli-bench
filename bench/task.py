"""The benchmark task: one workflow, scored against a rubric.

Design constraints, in order of importance:

1. **Every sub-answer is independently machine-checkable.** Completion is a
   percentage, not a boolean, so a run that gets three of five answers is
   reported as 60% rather than "failed". Weak models are expected to fail
   partially, and that gradation is data.
2. **The task is tool-intensive by construction.** Every item requires reading
   real repository state; none can be answered from the model's priors.
3. **One item deliberately rewards filtering before context.** Counting files
   under a directory is one shell command computed server-side, or a walk that
   pulls every listing into the context window. That asymmetry is the thing
   under study, so it must be in the task rather than assumed.
4. **Answers are stable.** The fixture is pinned to a tag, so ground truth does
   not drift between runs or between researchers reproducing the work.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

FIXTURE_REPO = "Lamb-Project/aawd-e1-fixture"
FIXTURE_TAG = "fixture-v1"


@dataclass(frozen=True)
class RubricItem:
    key: str
    question: str
    check: Callable[[str], bool]
    rationale: str


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _contains_all(*needles: str) -> Callable[[str], bool]:
    def check(answer: str) -> bool:
        a = _norm(answer)
        return all(_norm(n) in a for n in needles)
    return check


def _has_number(n: int) -> Callable[[str], bool]:
    def check(answer: str) -> bool:
        # accept the number anywhere, but not as part of a longer number
        return bool(re.search(rf"(?<!\d){n}(?!\d)", answer or ""))
    return check


RUBRIC: tuple[RubricItem, ...] = (
    RubricItem(
        key="default_branch",
        question="What is the repository's default branch?",
        check=_contains_all("main"),
        rationale="Single metadata lookup. Cheapest possible item; both surfaces "
                  "expose it directly.",
    ),
    RubricItem(
        key="top_level_dirs",
        question="Name the top-level directories in the repository.",
        check=_contains_all("pre-course", "week-01", "week-02", "week-03"),
        rationale="One listing. Tests whether the agent returns the set or "
                  "wanders into subdirectories.",
    ),
    RubricItem(
        key="readme_h1",
        question="What is the first heading (the H1) of README.md?",
        check=_contains_all("Software Engineering Educational Demos"),
        rationale="Requires reading file contents, not metadata. The emoji in the "
                  "real heading is deliberately not required.",
    ),
    RubricItem(
        key="tags",
        question="What git tags exist in the repository?",
        check=_contains_all(FIXTURE_TAG),
        rationale="A distinct API surface from branches; some tool registries "
                  "expose it and some do not.",
    ),
    RubricItem(
        key="file_count",
        question="How many files are in the week-01 directory tree?",
        check=_has_number(31),
        rationale="THE DISCRIMINATING ITEM. A CLI can compute this server-side in "
                  "one command. A tool registry without an aggregate operation "
                  "must walk the tree and count by reasoning over every listing "
                  "pulled into context.",
    ),
)

ARM_PREAMBLE = {
    "cli": ("You have the authenticated GitHub CLI (`gh`) and `git` available "
            "through your shell. Use them for every GitHub operation."),
    "mcp": ("You have GitHub tools available through an attached MCP server. "
            "Use them for every GitHub operation."),
}


def prompt_for(arm: str) -> str:
    """The task, prefixed with what this arm actually has.

    Experiment 1 told neither arm what was available, and qwen-code's CLI arm
    consequently never touched the CLI — it reached for a generic web-fetch tool
    in every run, so its "CLI" figures were web-API figures. Naming the surface
    is not a thumb on the scale; an arm that does not know its tools exist is
    not the arm we think we are measuring.
    """
    return ARM_PREAMBLE.get(arm, "") + "\n\n" + PROMPT


PROMPT = f"""Working with the GitHub repository {FIXTURE_REPO}, carry out these \
five steps in order. Use your available tools to find the real answers — do not \
guess. Keep each answer to one short line.

1. {RUBRIC[0].question}
2. {RUBRIC[1].question}
3. {RUBRIC[2].question}
4. {RUBRIC[3].question}
5. {RUBRIC[4].question}

When all five are done, output a numbered list of the five answers and nothing else."""


@dataclass
class Score:
    items: dict[str, bool] = field(default_factory=dict)

    @property
    def completed(self) -> int:
        return sum(1 for v in self.items.values() if v)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def pct(self) -> float:
        return round(100.0 * self.completed / max(1, self.total), 1)


def score(answer: str) -> Score:
    """Score a final answer against the rubric.

    Deliberately lenient about form and strict about content: the agent may
    number, bullet or prose its answers, but the facts must be right. Scoring the
    formatting would measure instruction-following, which is a different paper.
    """
    return Score({item.key: bool(item.check(answer or "")) for item in RUBRIC})
