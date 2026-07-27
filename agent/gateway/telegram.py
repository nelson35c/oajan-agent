"""Telegram gateway — reach Oajan from the Telegram app.

A messaging gateway is just another frontend over the same `run_turn` core: for
each incoming message we look up that chat's conversation, run a turn, and send
the reply back. Built raw on the Telegram Bot API with long-polling — no bot
framework, just `requests`.

Authorization is enforced up front: only user IDs in TELEGRAM_ALLOWED_IDS get a
real reply, because the agent can trigger side-effecting tools (send email,
create events). An unknown sender is told their own ID so it can be allowlisted.
"""

import os
import time

import requests
from dotenv import load_dotenv

from agent.loop import run_turn, SYSTEM_PROMPT

load_dotenv()

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_API = f"https://api.telegram.org/bot{_TOKEN}"

# Per-chat conversation state. In-RAM for now; sessions/memory come next chunk.
_conversations = {}


def _allowed_ids():
    raw = os.getenv("TELEGRAM_ALLOWED_IDS", "")
    return {int(x) for x in raw.replace(" ", "").split(",") if x}


def _get_updates(offset, timeout=30):
    r = requests.get(
        f"{_API}/getUpdates",
        params={"offset": offset, "timeout": timeout},
        timeout=timeout + 10,
    )
    r.raise_for_status()
    return r.json().get("result", [])


def _send(chat_id, text):
    requests.post(
        f"{_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )


def _handle(update):
    msg = update.get("message")
    if not msg or "text" not in msg:
        return
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg["text"]
    print(f"[telegram] {user_id} → {text!r}")

    if user_id not in _allowed_ids():
        _send(chat_id, f"Not authorized. Your Telegram ID is {user_id} — add it to "
                       f"TELEGRAM_ALLOWED_IDS in .env to enable Oajan.")
        return

    if text.strip() == "/start":
        _send(chat_id, "Oajan here. Ask me anything.")
        return

    messages = _conversations.setdefault(
        chat_id, [{"role": "system", "content": SYSTEM_PROMPT}]
    )
    messages.append({"role": "user", "content": text})
    answer = run_turn(messages)
    _send(chat_id, answer)


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
