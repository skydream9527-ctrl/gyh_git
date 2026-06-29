"""Voice service: ASR (audio → text) and TTS (text → wav bytes).

Both routes go through the Mify gateway and reuse MIFY_GATEWAY_* config; no
new secret is introduced. Both use Xiaomi MiMo's chat-completions API shape
documented at platform.xiaomimimo.com/docs:

- ASR: `mimo-v2.5` with an `input_audio` content block + a verbatim-transcribe
  prompt. The transcript may come back in `message.content` or, for the
  thinking models, in `reasoning_content`.
- TTS: `mimo-v2.5-tts` (or one of its sibling models) with the target text in
  the `assistant` message and the style instruction (optional) in the `user`
  message; voice is selected via `audio.voice`. Response is base64-encoded
  audio in `message.audio.data`. We request `wav` so a browser <audio> element
  can play it directly without re-muxing.
"""
from __future__ import annotations

import base64
import json
import logging

import httpx

from ..core.config import get_settings
from ..core.errors import APIError, ErrorCode

log = logging.getLogger(__name__)

_REQUEST_TIMEOUT_SEC = 60.0


def _assert_voice_enabled() -> None:
    s = get_settings()
    if not s.voice_enabled:
        raise APIError(
            503,
            ErrorCode.VOICE_DISABLED,
            "语音功能未启用（需要管理员开启 ICE_VOICE_ENABLED 并配置 MIFY_GATEWAY_*）",
        )


def _normalize_audio_mime(mime: str) -> str:
    """Coerce browser-reported MIME types to what the upstream model accepts.

    Recorded blobs from MediaRecorder commonly arrive as `audio/webm;codecs=opus`
    or `audio/mp4`. The MiMo audio-understanding endpoint expects the data URL
    prefix to identify the format; strip codec params and fall back to webm.
    """
    if not mime:
        return "audio/webm"
    base = mime.split(";", 1)[0].strip().lower()
    return base if base.startswith("audio/") else "audio/webm"


_TRANSCRIBE_PROMPT = (
    "请将这段音频中的语音逐字转写为纯文本，只输出转写结果本身，"
    "不要添加任何解释、前后缀、引号或额外说明；"
    "若无人说话则输出空字符串。"
)


async def transcribe(audio_bytes: bytes, mime: str) -> str:
    """ASR via MiMo audio-understanding (`mimo-v2.5` chat-completions).

    Args:
        audio_bytes: Raw audio file bytes (webm/opus/mp3/wav/ogg/m4a).
        mime: Browser-reported content-type; coerced to a clean `audio/*` form.

    Returns:
        Transcribed plain text (whitespace-stripped).

    Raises:
        APIError(503, VOICE_DISABLED): Feature flag off or gateway unconfigured.
        APIError(502, VOICE_GATEWAY_ERROR): Upstream non-200 or malformed response.
    """
    _assert_voice_enabled()
    s = get_settings()

    audio_mime = _normalize_audio_mime(mime)
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    data_url = f"data:{audio_mime};base64,{audio_b64}"

    url = f"{s.MIFY_GATEWAY_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {s.MIFY_GATEWAY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": s.ICE_VOICE_ASR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": data_url}},
                    {"type": "text", "text": _TRANSCRIBE_PROMPT},
                ],
            }
        ],
        "max_completion_tokens": 1024,
    }

    log.info(
        "voice.asr request bytes=%d mime=%s model=%s",
        len(audio_bytes), audio_mime, s.ICE_VOICE_ASR_MODEL,
    )
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SEC) as cli:
            resp = await cli.post(url, headers=headers, json=payload)
    except httpx.HTTPError as e:
        raise APIError(502, ErrorCode.VOICE_GATEWAY_ERROR, f"ASR gateway error: {e}")

    if resp.status_code != 200:
        body = resp.text[:300]
        raise APIError(
            502, ErrorCode.VOICE_GATEWAY_ERROR,
            f"ASR upstream {resp.status_code}: {body}",
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise APIError(502, ErrorCode.VOICE_GATEWAY_ERROR, f"ASR bad JSON: {e}")

    msg = ((data.get("choices") or [{}])[0] or {}).get("message") or {}
    # Thinking-model responses can land in `reasoning_content` while
    # `content` is the empty string. Prefer non-empty content; fall back to
    # reasoning_content when content is blank.
    text = (msg.get("content") or "").strip()
    if not text:
        text = (msg.get("reasoning_content") or "").strip()
    if not text:
        log.warning("voice.asr empty text usage=%s", data.get("usage"))
    return text


async def synthesize(text: str, voice: str) -> bytes:
    """TTS via MiMo `mimo-v2.5-tts` (chat-completions, non-streaming).

    The MiMo TTS API puts the *target broadcast text* in the `assistant`
    message; the `user` message is reserved for an optional style instruction.
    We send a minimal placeholder user instruction so behavior is consistent
    across voices that require one (e.g. voicedesign). Output is requested as
    `wav` so it can be served straight to a browser <audio> element.

    Args:
        text: Text to synthesize. Caller pre-truncates to a sane limit.
        voice: Built-in voice ID (e.g. `Chloe`, `Mia`, `冰糖`, `mimo_default`).

    Returns:
        Complete WAV bytes ready for `Response(media_type="audio/wav")`.

    Raises:
        APIError(503, VOICE_DISABLED), APIError(502, VOICE_GATEWAY_ERROR).
    """
    _assert_voice_enabled()
    s = get_settings()

    url = f"{s.MIFY_GATEWAY_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {s.MIFY_GATEWAY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": s.ICE_VOICE_TTS_MODEL,
        "messages": [
            {"role": "user", "content": "用自然、清晰的语调朗读下面的文本。"},
            {"role": "assistant", "content": text},
        ],
        "audio": {
            "format": "wav",
            "voice": voice,
        },
    }

    log.info(
        "voice.tts request len=%d voice=%s model=%s",
        len(text), voice, s.ICE_VOICE_TTS_MODEL,
    )
    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SEC) as cli:
            resp = await cli.post(url, headers=headers, json=payload)
    except httpx.HTTPError as e:
        raise APIError(502, ErrorCode.VOICE_GATEWAY_ERROR, f"TTS gateway error: {e}")

    if resp.status_code != 200:
        body = resp.text[:300]
        raise APIError(
            502, ErrorCode.VOICE_GATEWAY_ERROR,
            f"TTS upstream {resp.status_code}: {body}",
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise APIError(502, ErrorCode.VOICE_GATEWAY_ERROR, f"TTS bad JSON: {e}")

    msg = ((data.get("choices") or [{}])[0] or {}).get("message") or {}
    audio_obj = msg.get("audio") or {}
    audio_b64 = audio_obj.get("data") if isinstance(audio_obj, dict) else None
    if not audio_b64:
        raise APIError(
            502, ErrorCode.VOICE_GATEWAY_ERROR,
            "TTS empty audio in response",
        )

    try:
        return base64.b64decode(audio_b64)
    except (ValueError, TypeError) as e:
        raise APIError(502, ErrorCode.VOICE_GATEWAY_ERROR, f"TTS bad base64: {e}")
