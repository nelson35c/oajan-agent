"""Observability seam. All developer-facing trace output flows through here,
so rendering lives in one place. Two backends attach here without the loop
knowing: a `--verbose` printer, and (optionally) LangFuse.

LangFuse is enabled only when LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY are set;
otherwise every hook below is a cheap no-op. `turn()` opens one LangFuse trace
per user turn; the LLM calls nest under it automatically because llm.py uses
LangFuse's OpenAI drop-in, which reads the current trace context.
"""

import os
from contextlib import contextmanager

from dotenv import load_dotenv

load_dotenv()

_verbose = False

_lf = None
_lf_ready = False


def set_verbose(value):
    global _verbose
    _verbose = value


def is_verbose():
    return _verbose


# ----- LangFuse wiring ---------------------------------------------------

def langfuse_enabled():
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def _client():
    """Lazily build (and memoize) the LangFuse client, or None if unconfigured."""
    global _lf, _lf_ready
    if _lf_ready:
        return _lf
    _lf_ready = True
    if not langfuse_enabled():
        return None
    try:
        from langfuse import get_client
        _lf = get_client()
    except Exception:
        _lf = None
    return _lf


def _last_user_content(messages):
    for m in reversed(messages):
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        if role == "user":
            return m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
    return None


@contextmanager
def turn(messages):
    """Wrap one agent turn as a LangFuse trace. Yields the span (or None)."""
    client = _client()
    if client is None:
        yield None
        return
    with client.start_as_current_observation(
        name="oajan-turn",
        as_type="agent",
        input=_last_user_content(messages),
    ) as span:
        try:
            yield span
        finally:
            client.flush()


def set_turn_output(span, output):
    if span is not None:
        span.update(output=output)


# ----- verbose printer ---------------------------------------------------

def _emit(line):
    if _verbose:
        print(line)


def tool_call(step, name, args):
    _emit(f"[{step}] → {name}({args})")


def tool_result(step, result):
    _emit(f"[{step}] ← {result}")


def memory_recall(hits):
    if not hits:
        _emit("· memory: no relevant recalls")
        return
    _emit(f"· memory: recalled {len(hits)}")
    for h in hits:
        _emit(f"    - {round(h['similarity'], 3)} | {h['content'][:60]}")


def retry(attempt, error):
    _emit(f"retry {attempt}: tool-call generation failed, retrying")
