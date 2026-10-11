"""Server-side proxy to ElevenLabs for speech-to-text and text-to-speech.

The browser never sees the ElevenLabs key: it talks only to these two endpoints,
and the key is read here from the environment. If the key is missing, or
ElevenLabs errors or times out, we return a clear status (503/502/504) with no
body of patient words, so the browser can fall back to the Web Speech API.

Privacy: we never log audio bytes or transcript text. Only status codes,
timings and sizes are logged.
"""
from __future__ import annotations

import logging
import os
import time

import httpx
from fastapi import APIRouter, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field

logger = logging.getLogger("callbell")

router = APIRouter()

# ElevenLabs REST (confirmed against the current API reference, not guessed):
#   STT: POST /v1/speech-to-text  (multipart) fields: model_id, file, language_code
#        -> JSON {text, language_code, language_probability, ...}
#   TTS: POST /v1/text-to-speech/{voice_id} (json) fields: text, model_id, language_code
#        -> audio bytes
ELEVEN_BASE = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1").rstrip("/")   # override only for tests
STT_MODEL_ID = "scribe_v2"
TTS_MODEL_ID = "eleven_multilingual_v2"

# A slow voice call must never leave a patient waiting; the browser falls back.
TRANSCRIBE_TIMEOUT = 8.0
SPEAK_TIMEOUT = 5.0

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5 MB
ACCEPTED_AUDIO_TYPES = {
    "audio/webm", "video/webm",      # MediaRecorder default on Chrome
    "audio/ogg", "application/ogg",
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mp4", "video/mp4", "audio/mpeg", "audio/m4a", "audio/x-m4a",
}


def _api_key() -> str:
    """Return the ElevenLabs key, or raise 503 so the browser falls back."""
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="voice service not configured")
    return key


def _voice_id() -> str:
    return os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb").strip()


def _lang_code(lang: str | None) -> str | None:
    """Reduce a tag such as 'es' or 'en-US' to an ISO-639-1 code, or None."""
    if not lang:
        return None
    code = lang.strip().replace("_", "-").split("-")[0].lower()
    return code or None


@router.post("/api/transcribe")
async def transcribe(file: UploadFile, lang: str | None = Form(default=None)):
    """Proxy audio to ElevenLabs Scribe. Returns {text, language}."""
    key = _api_key()
    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=422, detail="no audio")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="audio too large")
    # Browsers add parameters, e.g. Chrome sends "audio/webm;codecs=opus".
    base_type = (file.content_type or "").split(";")[0].strip().lower()
    if base_type and base_type not in ACCEPTED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="unsupported audio format")

    data = {"model_id": STT_MODEL_ID}
    code = _lang_code(lang)
    # English is what the page opens in for every patient, so it says nothing about what this
    # patient speaks. Passing it on would force Hindi or Spanish speech into English words.
    # Only a language the page was deliberately opened in (?lang=hi-IN) is passed as a hint;
    # otherwise ElevenLabs detects the language from the speech itself.
    if code and code != "en":
        data["language_code"] = code
    files = {"file": (file.filename or "audio", audio, file.content_type or "application/octet-stream")}

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=TRANSCRIBE_TIMEOUT) as http:
            response = await http.post(
                f"{ELEVEN_BASE}/speech-to-text",
                headers={"xi-api-key": key},
                data=data, files=files,
            )
    except httpx.TimeoutException:
        logger.warning("transcribe: ElevenLabs timed out after %.0fms", (time.monotonic() - started) * 1000)
        raise HTTPException(status_code=504, detail="voice service timed out")
    except httpx.HTTPError:
        logger.warning("transcribe: ElevenLabs request failed")
        raise HTTPException(status_code=502, detail="voice service error")

    elapsed_ms = (time.monotonic() - started) * 1000
    if response.status_code != 200:
        logger.warning("transcribe: ElevenLabs returned %d in %.0fms", response.status_code, elapsed_ms)
        raise HTTPException(status_code=502, detail="voice service error")

    try:
        payload = response.json()
    except ValueError:
        logger.warning("transcribe: ElevenLabs sent a non-JSON body")
        raise HTTPException(status_code=502, detail="voice service error")

    text = (payload.get("text") or "").strip()
    language = payload.get("language_code") or code
    logger.info("transcribe: ok in %.0fms, %d audio bytes, text %s",
                elapsed_ms, len(audio), "empty" if not text else "present")
    return {"text": text, "language": language}


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    lang: str | None = None


@router.post("/api/speak")
async def speak(body: SpeakRequest):
    """Proxy text to ElevenLabs TTS. Returns audio bytes (audio/mpeg)."""
    key = _api_key()
    # eleven_multilingual_v2 detects the language from the text itself; ElevenLabs
    # only accepts language_code on its Turbo/Flash v2.5 models, so we don't send it.
    payload: dict = {"text": body.text, "model_id": TTS_MODEL_ID}

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=SPEAK_TIMEOUT) as http:
            response = await http.post(
                f"{ELEVEN_BASE}/text-to-speech/{_voice_id()}",
                headers={"xi-api-key": key, "Content-Type": "application/json"},
                params={"output_format": "mp3_44100_128"},
                json=payload,
            )
    except httpx.TimeoutException:
        logger.warning("speak: ElevenLabs timed out after %.0fms", (time.monotonic() - started) * 1000)
        raise HTTPException(status_code=504, detail="voice service timed out")
    except httpx.HTTPError:
        logger.warning("speak: ElevenLabs request failed")
        raise HTTPException(status_code=502, detail="voice service error")

    elapsed_ms = (time.monotonic() - started) * 1000
    if response.status_code != 200:
        logger.warning("speak: ElevenLabs returned %d in %.0fms", response.status_code, elapsed_ms)
        raise HTTPException(status_code=502, detail="voice service error")

    logger.info("speak: ok in %.0fms, %d audio bytes", elapsed_ms, len(response.content))
    return Response(content=response.content, media_type="audio/mpeg")


def voice_status() -> str:
    """For /api/health: whether the server has an ElevenLabs key. Never returns the key."""
    return "elevenlabs" if os.getenv("ELEVENLABS_API_KEY", "").strip() else "not configured"
