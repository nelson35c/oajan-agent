import json
from pathlib import Path

_SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "sessions"
_SESSIONS_DIR.mkdir(exist_ok=True)


def _to_dict(message):
    """Normalize one message to a JSON-safe dict.

    The messages list is mixed: user/system/tool entries are already plain
    dicts, but the assistant replies are OpenAI SDK objects. Those are
    pydantic models, so .model_dump() converts them to plain dicts.
    """
    if isinstance(message, dict):
        return message
    return message.model_dump()


def save_session(session_id, messages):
    path = _SESSIONS_DIR / f"{session_id}.json"
    serializable = [_to_dict(m) for m in messages]
    path.write_text(json.dumps(serializable, indent=2))
    return path

_ALLOWED = {"role", "content", "tool_calls", "tool_call_id", "name"}

def _clean(message):
    return {k: v for k, v in message.items() if k in _ALLOWED and v is not None}


def load_session(session_id):
    path = _SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return [_clean(m) for m in raw if m.get("role") != "system"]


def list_sessions():
    """Most-recent-first list of (session_id, modified_time)."""
    files = sorted(_SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p.stem, p.stat().st_mtime) for p in files]