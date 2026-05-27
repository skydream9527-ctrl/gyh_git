"""Conversation history compaction.

When a conversation grows past `ICE_COMPACTION_THRESHOLD_MSGS` messages, the
oldest portion is summarized into one synthetic user message and the tail is
kept verbatim. The summary is cached per-conversation (keyed by a checksum of
the compacted range) so repeated turns don't re-run the LLM.

Pairing invariant: Anthropic / Claude rejects any conversation where an
`assistant.tool_use` block isn't followed by a matching `user.tool_result`
block. We adjust the split so that the summary boundary never lands inside
such a pair — if it would, we extend `keep_tail` backward until the first
kept message is a clean `user` or plain `assistant` record.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from ..core.config import get_settings
from ..core.storage import get_paths, read_json, write_json
from . import llm_gateway

log = logging.getLogger("compaction")


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _checksum(old_head: list[dict]) -> str:
    canonical = json.dumps(old_head, ensure_ascii=False, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_clean_boundary(msg: dict) -> bool:
    """True if this message can safely be the first kept message (i.e. it's
    not a tool_result-only user message that belongs with a prior tool_use)."""
    content = msg.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                return False  # this is a tool_result user msg — must keep its pair
            if isinstance(block, dict) and block.get("type") == "tool_use":
                return True  # an assistant with tool_use starts a unit
    # plain user / assistant text is a clean start
    return True


def _adjust_split(api_messages: list[dict], keep_last: int) -> int:
    """Return the split index (where old_head ends / keep_tail begins) such
    that the tail starts at a clean boundary. Extends the tail backward by up
    to `max_extend` steps to find one."""
    total = len(api_messages)
    if total <= keep_last:
        return 0
    split = total - keep_last
    max_extend = 10
    for _ in range(max_extend):
        if split <= 0:
            return 0
        if _is_clean_boundary(api_messages[split]):
            return split
        split -= 1
    # Give up: use the requested split. The LLM may return 400 — tough luck,
    # but better than a hard crash; the ws.py outer handler will catch.
    return max(0, total - keep_last)


async def _summarize(old_head: list[dict], model: str | None) -> str:
    """Ask the main model to summarize the compacted range."""
    system = (
        "你是对话历史摘要助手。用中文输出一段总结，必须保留：\n"
        "1) 用户所有明确的需求、决策、承诺；\n"
        "2) 所有文件名、SQL 语句、已产出的文件；\n"
        "3) 所有工具调用结果中的关键数据（表名、数值、结论）；\n"
        "4) 未解决的问题或待办。\n"
        "不要编造，不要省略可能会影响后续判断的细节。输出为 Markdown 要点列表，控制在 600 字以内。"
    )
    # Flatten old_head into a readable transcript for the summarizer.
    lines: list[str] = []
    for m in old_head:
        role = m.get("role", "?")
        content = m.get("content")
        if isinstance(content, str):
            lines.append(f"[{role}] {content}")
        elif isinstance(content, list):
            for block in content:
                bt = block.get("type") if isinstance(block, dict) else None
                if bt == "text":
                    lines.append(f"[{role}] {block.get('text', '')}")
                elif bt == "tool_use":
                    lines.append(
                        f"[{role}:tool_use] {block.get('name')} input={json.dumps(block.get('input') or {}, ensure_ascii=False)[:300]}"
                    )
                elif bt == "tool_result":
                    body = block.get("content", "")
                    if not isinstance(body, str):
                        body = json.dumps(body, ensure_ascii=False)[:300]
                    lines.append(f"[{role}:tool_result] {body[:300]}")
    transcript = "\n".join(lines)[:30000]  # cap for the summarizer input
    out = await llm_gateway.complete_once(
        system_prompt=system,
        messages=[{"role": "user", "content": transcript}],
        model=model,
        max_tokens=1024,
    )
    return (out.get("text") or "").strip()


async def maybe_compact(
    *, task_id: str, conv_id: str, api_messages: list[dict]
) -> list[dict]:
    """Return api_messages unchanged if under threshold, else a compacted list
    with one synthetic summary message followed by the clean tail.

    On any error, logs and returns the trailing `ICE_COMPACTION_KEEP_LAST`
    messages (which is what the caller would have used anyway, just without a
    summary).
    """
    s = get_settings()
    if not s.ICE_COMPACTION_ENABLED:
        return api_messages

    threshold = max(s.ICE_COMPACTION_KEEP_LAST, s.ICE_COMPACTION_THRESHOLD_MSGS)
    if len(api_messages) <= threshold:
        return api_messages

    split = _adjust_split(api_messages, s.ICE_COMPACTION_KEEP_LAST)
    if split <= 0:
        return api_messages
    old_head = api_messages[:split]
    keep_tail = api_messages[split:]
    checksum = _checksum(old_head)

    paths = get_paths()
    cache_path = paths.task_conversation_compact(task_id, conv_id)
    cache = read_json(cache_path, default=None)
    summary: str | None = None
    if isinstance(cache, dict) and cache.get("checksum") == checksum:
        summary = cache.get("summary")

    if summary is None:
        try:
            summary = await _summarize(old_head, model=None)
        except Exception as exc:
            log.warning("summarization failed (%s); returning truncated tail", exc)
            return keep_tail
        if not summary:
            log.warning("summarization empty; returning truncated tail")
            return keep_tail
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(
                cache_path,
                {
                    "checksum": checksum,
                    "summary": summary,
                    "summarized_msg_count": len(old_head),
                    "created_at": _now(),
                    "model": llm_gateway.resolve_model(None),
                },
            )
        except Exception as exc:
            log.warning("compaction cache write failed: %s", exc)

    synthetic = {"role": "user", "content": f"(历史摘要 · {len(old_head)} 条消息)\n{summary}"}
    return [synthetic, *keep_tail]
