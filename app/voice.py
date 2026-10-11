"""Speech to text for the patient page, through ElevenLabs Scribe.

The page records the patient while it listens and posts the recording here when they stop.
ElevenLabs detects the language by itself, so a patient can speak any language Scribe knows.

Needs ELEVENLABS_API_KEY in .env (never in the frontend, never in git). Without a key, or if
ElevenLabs fails or takes longer than 8 seconds, this answers with an error and the page uses
the transcript from the browser's own speech recognition instead. If that is empty too, the
page sends the press to the nurse.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger("callbell")
router = APIRouter()

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
MAX_AUDIO_BYTES = 5 * 1024 * 1024    # 10 seconds of speech is far below this
TIMEOUT_S = 8                         # the page waits 10 s, so give up first

# ISO 639-3 codes Scribe may return, mapped to the two-letter codes used elsewhere.
THREE_TO_TWO = {"eng": "en", "spa": "es", "cmn": "zh", "zho": "zh", "yue": "zh",
                "hin": "hi", "ara": "ar", "arb": "ar", "por": "pt"}


def normalize_language(code: str | None) -> str | None:
    """'es-US', 'spa', 'ES' -> 'es'. Empty or unknown shape -> None."""
    if not code:
        return None
    code = code.strip().lower().replace("_", "-").split("-")[0]
    code = THREE_TO_TWO.get(code, code)
    return code if len(code) == 2 else None


def elevenlabs_transcribe(audio: bytes, content_type: str) -> dict:
    """Send the recording to ElevenLabs Scribe. Returns {text, language}."""
    boundary = uuid.uuid4().hex
    ext = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4", "audio/wav": "wav"}.get(content_type, "webm")
    fields = {"model_id": os.getenv("ELEVENLABS_STT_MODEL", "scribe_v2"), "tag_audio_events": "false"}
    body = b"".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields.items()
    )
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="request.{ext}"\r\n'
             f"Content-Type: {content_type}\r\n\r\n").encode() + audio + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        ELEVENLABS_STT_URL, data=body, method="POST",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"],
                 "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        data = json.loads(resp.read())
    return {"text": (data.get("text") or "").strip(), "language": normalize_language(data.get("language_code"))}


@router.post("/api/transcribe")
async def transcribe(request: Request):
    """Body: the raw recording (audio/webm, audio/ogg, audio/mp4 or audio/wav).
    Returns {text, language}. 503 when no key is set, 502 when ElevenLabs fails."""
    if not os.getenv("ELEVENLABS_API_KEY"):
        raise HTTPException(status_code=503, detail="speech to text is not set up: add ELEVENLABS_API_KEY to .env")
    audio = await request.body()
    if not audio:
        return {"text": "", "language": None}
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="recording too long")
    content_type = request.headers.get("content-type", "audio/webm").split(";")[0].strip()
    try:
        return await run_in_threadpool(elevenlabs_transcribe, audio, content_type)
    except urllib.error.HTTPError as exc:
        # 401 means the key is wrong; the reason is in the server log, never sent to the page
        logger.warning("ElevenLabs speech to text refused (%s): %s", exc.code, exc.read()[:300])
        raise HTTPException(status_code=502, detail="speech to text failed")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("ElevenLabs speech to text failed: %s", exc)
        raise HTTPException(status_code=502, detail="speech to text failed")


@router.get("/api/voice/health")
def voice_health():
    """Whether speech to text is set up. Never shows the key."""
    return {"speech_to_text": "elevenlabs" if os.getenv("ELEVENLABS_API_KEY") else "browser only"}
