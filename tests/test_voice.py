"""Speech to text endpoint (app/voice.py). No network: ElevenLabs is replaced with a stand-in."""
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app import main, voice


@pytest.fixture
def c(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    return TestClient(main.app)


def test_without_a_key_the_page_is_told_to_use_browser_speech(c):
    assert c.post("/api/transcribe", content=b"abc", headers={"Content-Type": "audio/webm"}).status_code == 503
    assert c.get("/api/voice/health").json() == {"speech_to_text": "browser only"}


def test_recording_is_sent_to_elevenlabs_and_text_comes_back(c, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    seen = {}

    def fake(audio, content_type):
        seen.update(audio=audio, content_type=content_type)
        return {"text": "necesito otra almohada", "language": "es"}

    monkeypatch.setattr(voice, "elevenlabs_transcribe", fake)
    r = c.post("/api/transcribe?lang=en-US", content=b"\x1aE\xdf\xa3", headers={"Content-Type": "audio/webm;codecs=opus"})
    assert r.json() == {"text": "necesito otra almohada", "language": "es"}
    assert seen == {"audio": b"\x1aE\xdf\xa3", "content_type": "audio/webm"}
    assert c.get("/api/voice/health").json() == {"speech_to_text": "elevenlabs"}


def test_elevenlabs_failure_lets_the_page_fall_back(c, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")

    def down(audio, content_type):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(voice, "elevenlabs_transcribe", down)
    r = c.post("/api/transcribe", content=b"x", headers={"Content-Type": "audio/webm"})
    assert r.status_code == 502
    assert "test-key" not in r.text


def test_empty_recording_returns_no_text(c, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    assert c.post("/api/transcribe", content=b"").json() == {"text": "", "language": None}


def test_request_sent_to_elevenlabs_is_well_formed(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    captured = {}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"text": " hello ", "language_code": "eng"}'

    def fake_urlopen(req, timeout):
        captured.update(url=req.full_url, headers=dict(req.header_items()), body=req.data, timeout=timeout)
        return Resp()

    monkeypatch.setattr(voice.urllib.request, "urlopen", fake_urlopen)
    out = voice.elevenlabs_transcribe(b"AUDIO", "audio/webm")
    assert out == {"text": "hello", "language": "en"}
    assert captured["url"] == "https://api.elevenlabs.io/v1/speech-to-text"
    assert captured["headers"]["Xi-api-key"] == "test-key"
    assert b'name="model_id"\r\n\r\nscribe_v2' in captured["body"]
    assert b'filename="request.webm"' in captured["body"] and b"AUDIO" in captured["body"]
    assert captured["timeout"] == 8
