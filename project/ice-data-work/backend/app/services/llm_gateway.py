"""LLM 网关：mify 前缀路由 + Anthropic 直连 fallback + 无 key 降级。

统一流式接口：stream_chat() 产出标准事件 dict：
    {"type": "text", "delta": "..."}        # 文本增量
    {"type": "done", "content": "...", "usage": {...}}  # 结束
    {"type": "error", "message": "..."}

无 key 时降级为 mock 流（回显 + 提示），保证端到端可跑通（特性开关思想）。
"""
from __future__ import annotations

import json
import os
from typing import Iterator

import httpx

from app.core.config import get_settings


def llm_available() -> bool:
    s = get_settings()
    return bool(s.mify_api_key) or bool(os.environ.get("ANTHROPIC_API_KEY"))


def _route(model: str) -> str:
    """按 model 前缀决定协议。mify 网关统一前缀路由 4 协议。"""
    if model.startswith(("mify/", "gpt", "claude", "gemini", "qwen", "deepseek")):
        return "mify" if get_settings().mify_api_key else "anthropic"
    return "anthropic"


def stream_chat(
    messages: list[dict],
    *,
    model: str = "claude-sonnet-4",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Iterator[dict]:
    """流式对话。messages: [{"role": "system|user|assistant", "content": "..."}]。"""
    if not llm_available():
        yield from _mock_stream(messages)
        return

    protocol = _route(model)
    try:
        if protocol == "mify":
            yield from _stream_mify(messages, model, temperature, max_tokens)
        else:
            yield from _stream_anthropic(messages, model, temperature, max_tokens)
    except Exception as e:  # 网络/协议错误降级，不阻塞对话
        yield {"type": "error", "message": f"LLM 调用失败: {e}"}


def _stream_mify(messages, model, temperature, max_tokens) -> Iterator[dict]:
    """mify 网关（OpenAI 兼容 SSE）。"""
    s = get_settings()
    url = s.mify_base_url.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {s.mify_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model.removeprefix("mify/"),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    full = []
    with httpx.stream("POST", url, json=payload, headers=headers, timeout=120) as r:
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    full.append(delta)
                    yield {"type": "text", "delta": delta}
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
    yield {"type": "done", "content": "".join(full), "usage": {}}


def _stream_anthropic(messages, model, temperature, max_tokens) -> Iterator[dict]:
    """Anthropic Messages API（SSE）。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    url = base.rstrip("/") + "/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    # 拆分 system 与对话
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [{"role": m["role"], "content": m["content"]}
             for m in messages if m["role"] in ("user", "assistant")]

    payload = {
        "model": _anthropic_model(model),
        "system": system,
        "messages": convo,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    full = []
    with httpx.stream("POST", url, json=payload, headers=headers, timeout=120) as r:
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            try:
                evt = json.loads(line[6:])
                if evt.get("type") == "content_block_delta":
                    delta = evt.get("delta", {}).get("text", "")
                    if delta:
                        full.append(delta)
                        yield {"type": "text", "delta": delta}
            except json.JSONDecodeError:
                continue
    yield {"type": "done", "content": "".join(full), "usage": {}}


def _anthropic_model(model: str) -> str:
    mapping = {
        "claude-sonnet-4": "claude-sonnet-4-20250514",
        "claude-opus-4": "claude-opus-4-20250514",
    }
    return mapping.get(model, model if model.startswith("claude") else "claude-sonnet-4-20250514")


def _mock_stream(messages: list[dict]) -> Iterator[dict]:
    """无 key 降级：回显最后一条用户消息 + 说明。开发/演示用。"""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    reply = (
        f"[本地模拟回复 · LLM 未配置]\n\n"
        f"我收到了你的消息：\u201c{last_user[:80]}\u201d。\n"
        f"配置 MIFY_GATEWAY_API_KEY 或 ANTHROPIC_API_KEY 后将启用真实模型。"
    )
    for ch in _chunks(reply, 12):
        yield {"type": "text", "delta": ch}
    yield {"type": "done", "content": reply, "usage": {"mock": True}}


def _chunks(text: str, size: int) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]
