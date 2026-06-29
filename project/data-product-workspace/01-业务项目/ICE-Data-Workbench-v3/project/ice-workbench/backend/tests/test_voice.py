"""Voice (ASR / TTS) route + service smoke tests.

Strategy:
    - Patch `voice_svc.transcribe` / `voice_svc.synthesize` (the http-talking
      layer) to keep tests offline. The voice_svc is what we're protecting:
      gating logic (voice_enabled, AUDIO_TOO_LARGE) lives in the route, not
      the service, so mocking the service is sufficient to assert routing.
    - One test exercises the real `_assert_voice_enabled` path so the gate
      itself is verified, without needing a real httpx mock.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def auth_client(isolated_data_root, monkeypatch):
    """Authenticated client; tests can override voice_enabled per-test via
    monkeypatch inside the test body."""
    from app.core import deps

    async def fake_user():
        return {"id": "u1", "is_admin": False}

    app.dependency_overrides[deps.get_current_user] = fake_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _enable_voice(monkeypatch):
    """Flip voice_enabled on by setting the underlying env vars and clearing
    the settings cache. This exercises the real `voice_enabled` property."""
    monkeypatch.setenv("ICE_VOICE_ENABLED", "true")
    monkeypatch.setenv("MIFY_GATEWAY_BASE_URL", "http://stub.invalid")
    monkeypatch.setenv("MIFY_GATEWAY_API_KEY", "stub-key")
    from app.core import config as cfg
    cfg.get_settings.cache_clear()


# ---- gating ---------------------------------------------------------------

@pytest.mark.asyncio
async def test_asr_disabled_returns_voice_disabled(auth_client, monkeypatch):
    # Default: ICE_VOICE_ENABLED=false → service raises VOICE_DISABLED
    monkeypatch.delenv("ICE_VOICE_ENABLED", raising=False)
    from app.core import config as cfg
    cfg.get_settings.cache_clear()

    files = {"file": ("clip.webm", b"\x00\x01\x02", "audio/webm")}
    r = await auth_client.post("/api/v1/voice/asr", files=files)
    assert r.status_code == 503
    body = r.json()
    assert body["error_code"] == "VOICE_DISABLED"


@pytest.mark.asyncio
async def test_tts_disabled_returns_voice_disabled(auth_client, monkeypatch):
    monkeypatch.delenv("ICE_VOICE_ENABLED", raising=False)
    from app.core import config as cfg
    cfg.get_settings.cache_clear()

    r = await auth_client.post("/api/v1/voice/tts", json={"text": "你好"})
    assert r.status_code == 503
    assert r.json()["error_code"] == "VOICE_DISABLED"


# ---- ASR happy path -------------------------------------------------------

@pytest.mark.asyncio
async def test_asr_returns_text(auth_client, monkeypatch):
    _enable_voice(monkeypatch)

    captured: dict = {}

    async def fake_transcribe(audio_bytes: bytes, mime: str) -> str:
        captured["bytes_len"] = len(audio_bytes)
        captured["mime"] = mime
        return "今天天气怎么样"

    from app.services import voice_svc
    monkeypatch.setattr(voice_svc, "transcribe", fake_transcribe)

    files = {"file": ("clip.webm", b"audio-payload-bytes", "audio/webm")}
    r = await auth_client.post("/api/v1/voice/asr", files=files)
    assert r.status_code == 200
    assert r.json()["data"]["text"] == "今天天气怎么样"
    assert captured["bytes_len"] == len(b"audio-payload-bytes")
    assert captured["mime"] == "audio/webm"


@pytest.mark.asyncio
async def test_asr_oversized_audio(auth_client, monkeypatch):
    _enable_voice(monkeypatch)

    # Default cap is 5MB. Send 6MB.
    big = b"x" * (6 * 1024 * 1024)
    files = {"file": ("big.webm", big, "audio/webm")}
    r = await auth_client.post("/api/v1/voice/asr", files=files)
    assert r.status_code == 413
    assert r.json()["error_code"] == "AUDIO_TOO_LARGE"


@pytest.mark.asyncio
async def test_asr_empty_audio(auth_client, monkeypatch):
    _enable_voice(monkeypatch)

    files = {"file": ("empty.webm", b"", "audio/webm")}
    r = await auth_client.post("/api/v1/voice/asr", files=files)
    assert r.status_code == 400
    assert r.json()["error_code"] == "VALIDATION_ERROR"


# ---- TTS happy path -------------------------------------------------------

@pytest.mark.asyncio
async def test_tts_returns_wav(auth_client, monkeypatch):
    _enable_voice(monkeypatch)

    captured: dict = {}
    fake_wav = b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 20  # wav-ish bytes

    async def fake_synth(text: str, voice: str) -> bytes:
        captured["text"] = text
        captured["voice"] = voice
        return fake_wav

    from app.services import voice_svc
    monkeypatch.setattr(voice_svc, "synthesize", fake_synth)

    r = await auth_client.post("/api/v1/voice/tts", json={"text": "你好世界"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == fake_wav
    assert captured["text"] == "你好世界"
    # default voice from settings (MiMo built-in)
    assert captured["voice"] == "Chloe"


@pytest.mark.asyncio
async def test_tts_custom_voice(auth_client, monkeypatch):
    _enable_voice(monkeypatch)

    captured: dict = {}

    async def fake_synth(text: str, voice: str) -> bytes:
        captured["voice"] = voice
        return b"RIFF\x00\x00\x00\x00WAVE"

    from app.services import voice_svc
    monkeypatch.setattr(voice_svc, "synthesize", fake_synth)

    r = await auth_client.post(
        "/api/v1/voice/tts",
        json={"text": "test", "voice": "冰糖"},
    )
    assert r.status_code == 200
    assert captured["voice"] == "冰糖"


@pytest.mark.asyncio
async def test_tts_text_too_long_rejected_by_pydantic(auth_client, monkeypatch):
    _enable_voice(monkeypatch)

    too_long = "好" * 2001
    r = await auth_client.post("/api/v1/voice/tts", json={"text": too_long})
    # pydantic validation → 422 from FastAPI
    assert r.status_code == 422


# ---- system-config exposes voice_enabled ----------------------------------

@pytest.mark.asyncio
async def test_global_toggles_includes_voice_enabled(auth_client, monkeypatch):
    _enable_voice(monkeypatch)
    r = await auth_client.get("/api/v1/system-config/global-toggles")
    assert r.status_code == 200
    assert r.json()["data"]["voice_enabled"] is True


@pytest.mark.asyncio
async def test_global_toggles_voice_disabled_when_flag_off(auth_client, monkeypatch):
    monkeypatch.delenv("ICE_VOICE_ENABLED", raising=False)
    from app.core import config as cfg
    cfg.get_settings.cache_clear()
    r = await auth_client.get("/api/v1/system-config/global-toggles")
    assert r.status_code == 200
    assert r.json()["data"]["voice_enabled"] is False
