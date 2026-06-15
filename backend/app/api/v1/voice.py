"""Voice routes: ASR upload + TTS synthesize. Mobile PTT only.

Both routes require an authenticated user (JWT or Aegis); zero special
permission. Feature flag is checked inside `voice_svc` so a disabled feature
returns the standard error envelope rather than 404.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...core.deps import get_current_user
from ...core.errors import APIError, ErrorCode, ok
from ...services import voice_svc

router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice: str | None = None


@router.post("/asr")
async def asr(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    s = get_settings()
    cap = s.ICE_VOICE_AUDIO_MAX_MB * 1024 * 1024
    data = await file.read()
    if len(data) > cap:
        raise APIError(
            413, ErrorCode.AUDIO_TOO_LARGE,
            f"录音超过 {s.ICE_VOICE_AUDIO_MAX_MB}MB 上限",
        )
    if not data:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "录音文件为空")
    text = await voice_svc.transcribe(data, file.content_type or "audio/webm")
    return ok({"text": text})


@router.post("/tts")
async def tts(
    body: TTSRequest,
    user: dict = Depends(get_current_user),
):
    s = get_settings()
    voice = body.voice or s.ICE_VOICE_DEFAULT_TTS_VOICE
    audio = await voice_svc.synthesize(body.text, voice)
    # MiMo-V2.5-TTS returns WAV (24kHz PCM16 wrapped). Browsers play it via
    # <audio> directly. no-store keeps edge caches out of per-request URLs.
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )
