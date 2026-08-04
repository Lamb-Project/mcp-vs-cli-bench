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
