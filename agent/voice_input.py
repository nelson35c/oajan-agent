"""Microphone capture for the CLI. Records raw PCM from the default input
device until the user presses Enter, then packages it as WAV bytes for the STT
seam. Uses sounddevice's RawInputStream so no numpy is needed.
"""

import io
import wave

_SAMPLE_RATE = 16000  # 16 kHz mono is plenty for speech / Whisper
_CHANNELS = 1
_SAMPWIDTH = 2        # int16 = 2 bytes/sample


def record_until_enter():
    """Record from the mic until Enter is pressed. Returns WAV bytes (or None)."""
    import sounddevice as sd  # imported lazily so the CLI runs without it

    chunks = []

    def _callback(indata, frames, time, status):
        chunks.append(bytes(indata))

    with sd.RawInputStream(
        samplerate=_SAMPLE_RATE,
        channels=_CHANNELS,
        dtype="int16",
        callback=_callback,
    ):
        input()  # blocks this thread until the user hits Enter

    pcm = b"".join(chunks)
    if not pcm:
        return None
    return _to_wav_bytes(pcm)


def _to_wav_bytes(pcm):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPWIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()
