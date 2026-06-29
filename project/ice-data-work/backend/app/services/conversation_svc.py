"""会话服务：conversation.jsonl + turn.speaker + tool_calls.jsonl。

一个任务一条主会话。每个 Turn 带 speaker{type:user|twin|agent, id}。
追加型存储（.jsonl），符合 G3 追加语义。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.storage import paths
from app.core.storage.jsonio import append_jsonl, read_jsonl


def append_turn(
    task_id: str,
    *,
    speaker_type: str,
    speaker_id: str,
    content: str,
    tool_calls: list[dict] | None = None,
    turn_id: str | None = None,
    handoff: dict | None = None,
) -> dict:
    """追加一个对话回合。

    handoff（M7-T03，可选）：本回合由转交接力而来时记录 {from, to, reason}，
    用于 A2A 转交链可追溯与前端转交卡渲染。
    """
    turn = {
        "id": turn_id or f"turn_{uuid.uuid4().hex[:10]}",
        "speaker": {"type": speaker_type, "id": speaker_id},
        "content": content,
        "tool_calls": tool_calls or [],
        "ts": _now_iso(),
    }
    if handoff:
        turn["handoff"] = handoff
    append_jsonl(paths.task_conversation(task_id), turn)
    return turn


def get_conversation(task_id: str, *, limit: int | None = None) -> list[dict]:
    """读取会话所有回合。limit 取最近 N 条。"""
    turns = read_jsonl(paths.task_conversation(task_id))
    if limit is not None and len(turns) > limit:
        return turns[-limit:]
    return turns


def append_tool_call(
    task_id: str,
    *,
    tool: str,
    args: dict,
    result: dict | None = None,
    speaker_id: str = "",
    status: str = "ok",
) -> dict:
    """记录一次工具调用（tool_calls.jsonl）。"""
    record = {
        "id": f"tc_{uuid.uuid4().hex[:10]}",
        "tool": tool,
        "args": args,
        "result": result,
        "speaker_id": speaker_id,
        "status": status,
        "ts": _now_iso(),
    }
    append_jsonl(paths.task_tool_calls(task_id), record)
    return record


def get_tool_calls(task_id: str) -> list[dict]:
    return read_jsonl(paths.task_tool_calls(task_id))


def recent_turns_text(task_id: str, *, limit: int = 12) -> str:
    """近 N 轮对话的纯文本摘要（供上下文组装）。"""
    turns = get_conversation(task_id, limit=limit)
    lines: list[str] = []
    for t in turns:
        sp = t.get("speaker", {})
        label = f"{sp.get('type', '?')}:{sp.get('id', '?')}"
        ho = t.get("handoff")
        prefix = f"[接力自 {ho['from']}] " if ho else ""
        lines.append(f"[{label}] {prefix}{t.get('content', '')}")
    return "\n".join(lines)


def last_content_by(task_id: str, speaker_id: str, *, max_chars: int = 1200) -> str:
    """取某 speaker 最近一条非空产出（供 A2A 接手方注入前序产出摘要）。"""
    turns = get_conversation(task_id)
    for t in reversed(turns):
        if t.get("speaker", {}).get("id") == speaker_id and (t.get("content") or "").strip():
            return t["content"][:max_chars]
    return ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
