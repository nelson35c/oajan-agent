"""Speech-to-text seam. Mirrors llm.py: one file owns the STT provider, so
swapping it is a base-URL, key, and model change and nothing else. Defaults to
Groq's Whisper (`whisper-large-v3`) via its OpenAI-compatible endpoint.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")

_client = None


def available():
    """True when a transcription key is configured; features gate on this."""
    return bool(os.getenv("GROQ_API_KEY"))


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


def transcribe(audio_bytes, filename="audio.ogg"):
    """Transcribe raw audio bytes to text and return the transcript string."""
    response = _get_client().audio.transcriptions.create(
        model=_MODEL,
        file=(filename, audio_bytes),
    )
    return (response.text or "").strip()
