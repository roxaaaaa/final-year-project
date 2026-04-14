"""
Real-time TTS module (OpenAI `tts-1`).

Connects to the talking avatar on the client like this:
  1) Client receives feedback text from `/api/feedback/generate`.
  2) Client POSTs the same text to `/api/tts/speak` and receives `audio/mpeg` bytes.
  3) Web Audio API plays the buffer; an AnalyserNode drives mouth openness (amplitude lip sync).

Future improvements (not implemented here — keep server light):
  - Viseme / phoneme timelines from TTS providers that expose them → map to mouth shapes.
  - Wav2Lip or similar video lip sync → would reintroduce video, not the current architecture.
"""
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
# OpenAI speech input limit is 4096 characters
TTS_MAX_CHARS = 4096


async def synthesize_speech_mp3(text: str, voice: Optional[str] = None) -> bytes:
    """
    Low-latency speech synthesis suitable for streaming playback on the client.

    Uses OpenAI's HTTP API directly so we do not block the event loop with sync SDK calls.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for TTS")

    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("TTS text must not be empty")

    if len(cleaned) > TTS_MAX_CHARS:
        cleaned = cleaned[:TTS_MAX_CHARS]
        logger.warning("TTS text truncated to %s characters", TTS_MAX_CHARS)

    use_voice = voice or TTS_VOICE
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": TTS_MODEL,
        "voice": use_voice,
        "input": cleaned,
        "response_format": "mp3",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            logger.error("OpenAI TTS error %s: %s", response.status_code, response.text)
            response.raise_for_status()
        return response.content
