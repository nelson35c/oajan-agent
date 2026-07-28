"""Telegram gateway — reach Oajan from the Telegram app.

A messaging gateway is just another frontend over the same `run_turn` core: for
each incoming message we look up that chat's conversation, run a turn, and send
the reply back. Built raw on the Telegram Bot API with long-polling — no bot
framework, just `requests`.

Each chat maps to a stable session (`telegram-<chat_id>`), so conversations
persist across restarts and reuse the same long-term memory as the CLI. LangFuse
traces group by that session too. Authorization is enforced up front: only user
IDs in TELEGRAM_ALLOWED_IDS get a real reply, because the agent can trigger
side-effecting tools (send email, create events). An unknown sender is told its
own ID so it can be allowlisted.
"""

import os
import threading
import time

import requests
from dotenv import load_dotenv

from agent import stt
from agent.loop import run_turn, SYSTEM_PROMPT
from agent.memory.session_store import save_session, load_session
from agent.memory.store import save_memory, recall_memories

load_dotenv()

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_API = f"https://api.telegram.org/bot{_TOKEN}"
_MAX_LEN = 4096  # Telegram's per-message character limit

# Per-chat conversation state, kept in RAM and mirrored to sessions/*.json.
_conversations = {}


def _allowed_ids():
    raw = os.getenv("TELEGRAM_ALLOWED_IDS", "")
    return {int(x) for x in raw.replace(" ", "").split(",") if x}


def _session_id(chat_id):
    return f"telegram-{chat_id}"


# ----- Telegram Bot API --------------------------------------------------

def _get_updates(offset, timeout=30):
    r = requests.get(
        f"{_API}/getUpdates",
        params={"offset": offset, "timeout": timeout},
        timeout=timeout + 10,
    )
    r.raise_for_status()
    return r.json().get("result", [])


def _download_file(file_id):
    """Resolve a Telegram file_id to (bytes, filename) via getFile + download."""
    r = requests.get(f"{_API}/getFile", params={"file_id": file_id}, timeout=30)
    r.raise_for_status()
    path = r.json()["result"]["file_path"]
    data = requests.get(
        f"https://api.telegram.org/file/bot{_TOKEN}/{path}", timeout=60
    ).content
    filename = path.split("/")[-1] or "audio.ogg"
    # Telegram voice notes are Ogg Opus but land named .oga, which Groq's STT
    # rejects by extension; .ogg names the same container and is accepted.
    if filename.endswith(".oga"):
        filename = filename[:-4] + ".ogg"
    return data, filename


def _chunks(text):
    """Split a reply into pieces under Telegram's length cap, on line breaks."""
    text = text or ""
    while len(text) > _MAX_LEN:
        cut = text.rfind("\n", 0, _MAX_LEN)
        if cut <= 0:
            cut = _MAX_LEN
        yield text[:cut]
        text = text[cut:].lstrip("\n")
    if text:
        yield text


def _send(chat_id, text):
    for chunk in _chunks(text):
        requests.post(
            f"{_API}/sendMessage",
            json={"chat_id": chat_id, "text": chunk},
            timeout=30,
        )


def _send_typing(chat_id):
    requests.post(
        f"{_API}/sendChatAction",
        json={"chat_id": chat_id, "action": "typing"},
        timeout=30,
    )


def _typing_while(chat_id, stop):
    """Keep the 'typing…' indicator alive until `stop` is set (it fades ~5s)."""
    while not stop.is_set():
        try:
            _send_typing(chat_id)
        except Exception:
            pass
        stop.wait(4)


# ----- conversation state ------------------------------------------------

def _conversation(chat_id):
    """Return this chat's message list, restoring from disk on first touch."""
    messages = _conversations.get(chat_id)
    if messages is None:
        prior = load_session(_session_id(chat_id)) or []
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + prior
        _conversations[chat_id] = messages
    return messages


# ----- message handling --------------------------------------------------

def _resolve_text(chat_id, msg):
    """Return the user's text: the typed message, or a transcribed voice note.
    Returns None for unsupported messages (and reports voice/config problems)."""
    if "text" in msg:
        return msg["text"]

    media = msg.get("voice") or msg.get("audio")
    if not media:
        return None
    if not stt.available():
        _send(chat_id, "Voice isn't configured — set GROQ_API_KEY to enable "
                       "transcription.")
        return None
    try:
        audio_bytes, filename = _download_file(media["file_id"])
        transcript = stt.transcribe(audio_bytes, filename)
    except Exception as exc:
        _send(chat_id, f"Couldn't transcribe that: {exc}")
        return None
    if not transcript:
        _send(chat_id, "I couldn't make out any speech in that.")
        return None
    _send(chat_id, f"🎙️ heard: {transcript}")
    return transcript


def _handle(update):
    msg = update.get("message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]

    if user_id not in _allowed_ids():
        _send(chat_id, f"Not authorized. Your Telegram ID is {user_id} — add it to "
                       f"TELEGRAM_ALLOWED_IDS in .env to enable Oajan.")
        return

    text = _resolve_text(chat_id, msg)
    if text is None:
        return
    print(f"[telegram] {user_id} → {text!r}")

    command = text.strip().lower()
    if command == "/start":
        _send(chat_id, "Oajan here. Ask me anything.")
        return
    if command == "/reset":
        _conversations.pop(chat_id, None)
        save_session(_session_id(chat_id), [{"role": "system", "content": SYSTEM_PROMPT}])
        _send(chat_id, "Conversation reset.")
        return

    sid = _session_id(chat_id)
    messages = _conversation(chat_id)

    memories = recall_memories(text)
    if memories:
        block = "Relevant memories from past conversations:\n" + "\n".join(
            f"- {m['content']}" for m in memories
        )
        messages.append({"role": "system", "content": block})

    messages.append({"role": "user", "content": text})

    stop = threading.Event()
    typer = threading.Thread(target=_typing_while, args=(chat_id, stop), daemon=True)
    typer.start()
    try:
        answer = run_turn(messages, session_id=sid)
    finally:
        stop.set()

    _send(chat_id, answer)
    save_memory(sid, f"User: {text}\nAssistant: {answer}")
    save_session(sid, messages)


def run():
    if not _TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set in .env")

    started = time.time()
    print("Oajan Telegram gateway running. Ctrl+C to stop.")
    offset = None
    try:
        while True:
            try:
                updates = _get_updates(offset)
            except Exception as exc:
                print("poll error:", exc)
                time.sleep(3)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                # Skip a backlog of messages sent before the gateway started.
                msg = u.get("message") or {}
                if msg.get("date", 0) < started:
                    continue
                try:
                    _handle(u)
                except Exception as exc:
                    print("handle error:", exc)
    except KeyboardInterrupt:
        print("\nGateway stopped.")
