"""Voice proxy endpoints, with ElevenLabs mocked. No real network calls.

Each test replaces httpx.AsyncClient.post so nothing leaves the machine, which
keeps `python -m pytest` green offline and on GitHub.
"""
import httpx
import pytest
from fastapi.testclient import TestClient

from app import main, voice


@pytest.fixture
def client():
    return TestClient(main.app)


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None, content=b""):
        self.status_code = status_code
        self._json = json_body
        self.content = content

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def _patch_post(monkeypatch, handler):
    """Make every httpx.AsyncClient.post call `handler(url, **kwargs)`."""
    async def fake_post(self, url, **kwargs):
        return handler(url, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)


# --- transcribe -----------------------------------------------------------

def test_transcribe_success(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    seen = {}

    def handler(url, **kwargs):
        seen["url"] = url
        seen["data"] = kwargs.get("data")
        return _FakeResponse(200, {"text": "I need some water", "language_code": "en"})

    _patch_post(monkeypatch, handler)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"RIFFfakeaudio", "audio/webm")},
        data={"lang": "en-US"},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "I need some water", "language": "en"}
    assert seen["url"].endswith("/speech-to-text")
    assert seen["data"]["model_id"] == "scribe_v2"
    assert "language_code" not in seen["data"]        # the page default is not forced on the speech


def test_transcribe_passes_on_a_language_the_page_was_opened_in(client, monkeypatch):
    """?lang=hi-IN is a deliberate choice, so it is sent as a hint; plain English is not."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    seen = {}

    def handler(url, **kwargs):
        seen["data"] = kwargs.get("data")
        return _FakeResponse(200, {"text": "\u092e\u0941\u091d\u0947 \u0924\u094c\u0932\u093f\u092f\u093e \u091a\u093e\u0939\u093f\u090f", "language_code": "hi"})

    _patch_post(monkeypatch, handler)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"RIFFfakeaudio", "audio/webm")},
        data={"lang": "hi-IN"},
    )
    assert response.status_code == 200 and response.json()["language"] == "hi"
    assert seen["data"]["language_code"] == "hi"


def test_transcribe_missing_key_returns_503(client, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    def handler(url, **kwargs):
        raise AssertionError("ElevenLabs must not be called without a key")

    _patch_post(monkeypatch, handler)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"RIFFfakeaudio", "audio/webm")},
    )
    assert response.status_code == 503


def test_transcribe_timeout_returns_504(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def handler(url, **kwargs):
        raise httpx.TimeoutException("slow")

    _patch_post(monkeypatch, handler)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"RIFFfakeaudio", "audio/webm")},
    )
    assert response.status_code == 504


def test_transcribe_empty_transcript_is_returned_as_empty(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def handler(url, **kwargs):
        return _FakeResponse(200, {"text": "   ", "language_code": "en"})

    _patch_post(monkeypatch, handler)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"RIFFfakeaudio", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == ""


def test_transcribe_rejects_oversize_audio(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def handler(url, **kwargs):
        raise AssertionError("oversize audio must be refused before any call")

    _patch_post(monkeypatch, handler)
    big = b"x" * (voice.MAX_AUDIO_BYTES + 1)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", big, "audio/webm")},
    )
    assert response.status_code == 413


def test_transcribe_upstream_error_returns_502(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def handler(url, **kwargs):
        return _FakeResponse(401, {"detail": "bad key"})

    _patch_post(monkeypatch, handler)
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"RIFFfakeaudio", "audio/webm")},
    )
    assert response.status_code == 502


# --- speak -----------------------------------------------------------------

def test_speak_success_returns_audio(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-123")
    seen = {}

    def handler(url, **kwargs):
        seen["url"] = url
        seen["json"] = kwargs.get("json")
        return _FakeResponse(200, content=b"ID3fakeaudio")

    _patch_post(monkeypatch, handler)
    response = client.post("/api/speak", json={"text": "Housekeeping has your request.", "lang": "en"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"ID3fakeaudio"
    assert seen["url"].endswith("/text-to-speech/voice-123")
    assert seen["json"]["text"] == "Housekeeping has your request."


def test_speak_missing_key_returns_503(client, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

    def handler(url, **kwargs):
        raise AssertionError("ElevenLabs must not be called without a key")

    _patch_post(monkeypatch, handler)
    response = client.post("/api/speak", json={"text": "Hello", "lang": "en"})
    assert response.status_code == 503


def test_speak_timeout_returns_504(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def handler(url, **kwargs):
        raise httpx.TimeoutException("slow")

    _patch_post(monkeypatch, handler)
    response = client.post("/api/speak", json={"text": "Hello", "lang": "en"})
    assert response.status_code == 504


def test_speak_empty_text_is_refused(client, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    response = client.post("/api/speak", json={"text": "", "lang": "en"})
    assert response.status_code == 422


# --- real-browser details ----------------------------------------------------

def test_transcribe_accepts_chrome_codec_parameter(client, monkeypatch):
    """Chrome's MediaRecorder labels clips 'audio/webm;codecs=opus'."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    _patch_post(monkeypatch, lambda url, **kw: _FakeResponse(200, {"text": "a pillow please", "language_code": "en"}))
    response = client.post(
        "/api/transcribe",
        files={"file": ("clip.webm", b"fakeaudio", "audio/webm;codecs=opus")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "a pillow please"


def test_speak_does_not_send_language_code_to_multilingual_model(client, monkeypatch):
    """eleven_multilingual_v2 rejects language_code; it detects language from the text."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    seen = {}

    def handler(url, **kwargs):
        seen["json"] = kwargs.get("json")
        return _FakeResponse(200, content=b"ID3fakemp3")

    _patch_post(monkeypatch, handler)
    response = client.post("/api/speak", json={"text": "Housekeeping tiene su solicitud.", "lang": "es"})
    assert response.status_code == 200
    assert "language_code" not in seen["json"]


def test_health_says_whether_voice_is_configured(client, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert client.get("/api/health").json()["voice"] == "not configured"
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-test-not-real")
    body = client.get("/api/health").json()
    assert body["voice"] == "elevenlabs" and "sk-test" not in str(body)
