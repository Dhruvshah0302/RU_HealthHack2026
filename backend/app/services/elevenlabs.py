"""ElevenLabs speech-to-text (P0 for voice) and text-to-speech (P1, optional).
Check the current ElevenLabs API docs for model IDs and response fields before the demo."""
import httpx

from ..config import settings

BASE = "https://api.elevenlabs.io/v1"


class STTError(Exception):
    pass


async def speech_to_text(audio_bytes: bytes, filename: str, content_type: str) -> tuple[str, str]:
    """Returns (transcript, language_code). Raises STTError on failure."""
    if not settings.elevenlabs_api_key:
        raise STTError("ELEVENLABS_API_KEY not set")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE}/speech-to-text",
            headers={"xi-api-key": settings.elevenlabs_api_key},
            data={"model_id": settings.elevenlabs_stt_model},
            files={"file": (filename, audio_bytes, content_type)},
        )
    if r.status_code != 200:
        raise STTError(f"ElevenLabs STT {r.status_code}: {r.text[:200]}")
    body = r.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise STTError("Empty transcript")
    return text, body.get("language_code", "en")


async def text_to_speech(text: str) -> bytes:
    """Returns MP3 bytes for the confirmation message."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{BASE}/text-to-speech/{settings.elevenlabs_tts_voice_id}",
            headers={"xi-api-key": settings.elevenlabs_api_key, "Accept": "audio/mpeg"},
            json={"text": text, "model_id": settings.elevenlabs_tts_model},
        )
    r.raise_for_status()
    return r.content
