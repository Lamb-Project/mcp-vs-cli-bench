"""LiteLLM callback: append one JSONL line per upstream request.

qwen-code reports a single cumulative usage record per run, so the per-turn
compounding shape -- the thing H2 is actually about -- is invisible from the
scaffold. Sitting the proxy between scaffold and llama-server recovers it, and
gives a token count that does not depend on the scaffold's own accounting.

The field that matters is prompt_tokens_details.cached_tokens: llama-server
reports it, Ollama does not, and it is why the grid runs on GLM. Verifying it
survives the proxy hop is half the point of putting LiteLLM in the chain.
"""
import json
import os
import threading

from litellm.integrations.custom_logger import CustomLogger

LOG_PATH = os.environ.get("E1_USAGE_LOG", "/tmp/e1-usage.jsonl")
_lock = threading.Lock()


def _as_dict(obj):
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    for attr in ("model_dump", "dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:  # noqa: BLE001
                pass
    return {k: v for k, v in vars(obj).items() if not k.startswith("_")}


def _called_tools(response_obj):
    """Names of tools the model called on this turn, in order.

    Reads the response rather than the request: the request carries the
    catalogue, the response carries the use. Defensive throughout — a telemetry
    callback must never break the request path.
    """
    out = []
    try:
        choices = getattr(response_obj, "choices", None) or []
        for ch in choices:
            # Streamed responses carry the assembled call on `delta` rather
            # than `message`. Hosted models stream and local ones did not, so
            # checking only `message` recorded full registers for local cells
            # and zero for hosted ones — a gap that looked like models simply
            # not calling tools, on runs that had completed a write workflow.
            msg = (getattr(ch, "message", None)
                   or (ch.get("message") if isinstance(ch, dict) else None)
                   or getattr(ch, "delta", None)
                   or (ch.get("delta") if isinstance(ch, dict) else None))
            if msg is None:
                continue
            calls = getattr(msg, "tool_calls", None) or (
                msg.get("tool_calls") if isinstance(msg, dict) else None) or []
            for c in calls:
                fn = getattr(c, "function", None) or (
                    c.get("function") if isinstance(c, dict) else None)
                nm = getattr(fn, "name", None) or (
                    fn.get("name") if isinstance(fn, dict) else None)
                if nm:
                    out.append(nm)
    except Exception:
        return out
    return out


class UsageLogger(CustomLogger):
    def _write(self, kwargs, response_obj, start_time, end_time):
        try:
            usage = _as_dict(getattr(response_obj, "usage", None))
            details = _as_dict(usage.get("prompt_tokens_details"))
            messages = kwargs.get("messages") or []
            tools = kwargs.get("tools") or []
            record = {
                # A per-batch tag cannot be set from the client: this callback
                # runs inside the proxy, so a client env var is invisible here,
                # and every Experiment 1 request was tagged with whatever the
                # proxy happened to start with. A timestamp is reliable across
                # all four clients and lets the analysis segment the log by run
                # window, which is what the tag was for.
                "ts": start_time.isoformat() if hasattr(start_time, "isoformat")
                      else None,
                "tag": os.environ.get("E1_RUN_TAG", "untagged"),
                "model": kwargs.get("model"),
                "n_messages": len(messages),
                "n_tools": len(tools),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                # llama-server's cached-prefix count, the reason for GLM
                "cached_tokens": details.get("cached_tokens"),
                "latency_s": round((end_time - start_time).total_seconds(), 2)
                if hasattr(end_time, "__sub__") else None,
                # The tools the model actually CALLED on this turn, by name.
                # Recorded here rather than parsed from each scaffolding's
                # stdout because every arm crosses the proxy, so one
                # implementation covers all of them and none can report a
                # fabricated zero. Hermes prints only its final answer in
                # one-shot mode and emits no tool events at all, which is what
                # forced this; the register is scaffolding-independent now.
                "tool_calls": _called_tools(response_obj),
                # The names OFFERED this turn — catalogue size is the thing the
                # whole study is about, and len() alone cannot show which tools
                # a catalogue actually contributes.
                "tool_names_offered": [
                    (t.get("function") or {}).get("name")
                    for t in tools if isinstance(t, dict)][:80],
            }
            pt = record["prompt_tokens"] or 0
            ct = record["cached_tokens"] or 0
            record["prefilled"] = pt - ct
            with _lock, open(LOG_PATH, "a") as fh:
                fh.write(json.dumps(record) + "\n")
        except Exception as exc:  # never break the request path over telemetry
            with _lock, open(LOG_PATH, "a") as fh:
                fh.write(json.dumps({"error": repr(exc)}) + "\n")

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._write(kwargs, response_obj, start_time, end_time)

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._write(kwargs, response_obj, start_time, end_time)


handler = UsageLogger()
