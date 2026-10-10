"""Spoken Hebrew for Nifra reminders — Azure Speech, the woman's voice "Hila" (he-IL-HilaNeural).

One voice for every agent and every channel (browser today, the Android app next): the server
turns text into an MP3 and the client just plays it. Free tier (F0): 500K characters a month and
it never bills — past the quota Azure refuses, `synthesize` raises, and the client falls back to
the browser's own voice. Identical text is generated once (in-process LRU), so a replay costs nothing.
"""
from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from xml.sax.saxutils import escape

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
MAX_CHARS = 1500             # a brief is ~300; anything longer isn't a reminder
_CACHE: "OrderedDict[str, bytes]" = OrderedDict()
_CACHE_MAX = 300


class TtsUnavailable(RuntimeError):
    pass


def enabled() -> bool:
    return bool(settings.AZURE_SPEECH_KEY)


def _ssml(text: str) -> str:
    return (f"<speak version='1.0' xml:lang='he-IL'><voice name='{settings.AZURE_SPEECH_VOICE}'>"
            f"<prosody rate='-4%'>{escape(text)}</prosody></voice></speak>")


async def synthesize(text: str) -> bytes:
    """MP3 bytes for `text`. Raises TtsUnavailable (not configured, quota, network)."""
    text = " ".join((text or "").split())[:MAX_CHARS]
    if not text:
        raise TtsUnavailable("empty")
    if not enabled():
        raise TtsUnavailable("AZURE_SPEECH_KEY not set")
    key = hashlib.sha1(f"{settings.AZURE_SPEECH_VOICE}|{text}".encode()).hexdigest()
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    url = f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            r = await http.post(url, content=_ssml(text).encode(), headers={
                "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "nifraim",
            })
    except httpx.HTTPError as e:
        raise TtsUnavailable(f"network: {e}") from e
    if r.status_code != 200 or not r.content:
        # 429/403 on F0 = this month's free quota is used up — the browser voice takes over
        logger.warning("tts: azure answered %s", r.status_code)
        raise TtsUnavailable(f"azure {r.status_code}")
    _CACHE[key] = r.content
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return r.content
