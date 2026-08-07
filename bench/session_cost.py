#!/usr/bin/env python3
"""Total the token cost of a Claude Code session from its transcript.

Section 2.10 discloses what producing the study cost. Draft 8 reported one
six-day session; work continued in a later session, and a disclosure that
silently omits the second is worse than none.

The counter is validated against the published draft-8 figures before being
trusted on any new session: if it cannot reproduce a number already in print
from the same transcript, it is not measuring what that number measured.

Usage:  python3 -m bench.session_cost <session-id> [<session-id> ...]
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

PROJ = (pathlib.Path.home() / ".claude/projects"
        / "-Users-granludo-Documents-ludo-claude-ludo-writting-workshop")

# The draft-8 disclosure table, to check the counter against.
#
# The totals do NOT match the finished transcript, and the reason is the point:
# draft 8's figures were taken while that session was still running ("2,181
# assistant turns as of this draft"), and it went on for another 41 turns after
# the number was written down. The stable anchor is the Opus turn count, 2,153,
# which the counter reproduces exactly; the Fable count moved from 26 to 67 and
# carried every total with it. A disclosure measured from inside the session it
# describes can only ever be a snapshot.
V8 = {"session": "6c1c6231-2001-4961-8ec8-0c155193b708",
      "cache_read": 955_675_013, "cache_write": 35_913_849, "uncached": 4_034,
      "total_input": 991_592_896, "output": 2_346_962, "turns": 2_181,
      "opus_turns": 2_153}


def totals(session_id: str) -> dict:
    path = PROJ / f"{session_id}.jsonl"
    if not path.exists():
        raise SystemExit(f"no transcript at {path}")
    cr = cw = un = out = turns = 0
    models: Counter = Counter()
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = d.get("message") or {}
            if d.get("type") != "assistant" or not isinstance(msg, dict):
                continue
            u = msg.get("usage") or {}
            if not u:
                continue
            turns += 1
            models[msg.get("model") or "unknown"] += 1
            cr += u.get("cache_read_input_tokens") or 0
            cw += u.get("cache_creation_input_tokens") or 0
            un += u.get("input_tokens") or 0
            out += u.get("output_tokens") or 0
    return {"session": session_id, "cache_read": cr, "cache_write": cw,
            "uncached": un, "total_input": cr + cw + un, "output": out,
            "turns": turns, "models": dict(models)}


def show(t: dict) -> None:
    print(f"  turns            {t['turns']:>15,}")
    print(f"  input, cached    {t['cache_read']:>15,}")
    print(f"  input, written   {t['cache_write']:>15,}")
    print(f"  input, uncached  {t['uncached']:>15,}")
    print(f"  TOTAL INPUT      {t['total_input']:>15,}")
    print(f"  output           {t['output']:>15,}")
    if t["output"]:
        print(f"  input:output     {round(t['total_input']/t['output']):>15}:1")
    if t["total_input"]:
        print(f"  cache share      {100*t['cache_read']/t['total_input']:>14.1f}%")
    print(f"  models           {t['models']}")


def main() -> None:
    ids = sys.argv[1:]
    if not ids:
        # Default: validate against the published numbers.
        print(f"validating counter against draft 8's disclosure "
              f"(session {V8['session'][:8]})\n")
        t = totals(V8["session"])
        show(t)
        print()
        # The anchor: Opus turns are settled and must match exactly.
        opus = t["models"].get("claude-opus-5", 0)
        ok = opus == V8["opus_turns"]
        print(f"  {'OK  ' if ok else 'FAIL'} {'opus turns':<14} "
              f"paper={V8['opus_turns']:>14,}  transcript={opus:>14,}")
        for k in ("cache_read", "cache_write", "uncached", "total_input",
                  "output", "turns"):
            drift = t[k] - V8[k]
            print(f"  {'same' if not drift else 'grew'} {k:<14} "
                  f"paper={V8[k]:>14,}  transcript={t[k]:>14,}  "
                  f"({drift:+,})")
        print(f"\n  counter {'reproduces' if ok else 'DOES NOT reproduce'} "
              f"the settled Opus turn count")
        print("  totals exceed the published table because draft 8 measured a "
              "session that had not finished;\n  the Fable pass grew from 26 "
              "turns to 67 afterwards. Draft 9 should report final figures.")
        raise SystemExit(0 if ok else 1)

    grand = None
    for sid in ids:
        t = totals(sid)
        print(f"\nsession {sid}")
        show(t)
        if grand is None:
            grand = {k: v for k, v in t.items() if isinstance(v, int)}
        else:
            for k in grand:
                grand[k] += t[k]
    if len(ids) > 1:
        print("\ncombined")
        grand["models"] = {}
        show(grand)


if __name__ == "__main__":
    main()
