_verbose = False

def set_verbose(value):
    global _verbose
    _verbose = value

"""Observability seam. All developer-facing trace output flows through here,
so rendering lives in one place — and a backend like LangFuse can attach
later by changing this module's internals, without touching the loop."""

_verbose = False


def set_verbose(value):
    global _verbose
    _verbose = value


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
