"""Multi-conversation per task (spec 3.5, 4.6)."""
from __future__ import annotations

import fcntl
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ..core.errors import APIError, ErrorCode
from ..core.storage import file_transaction, get_index_db, get_paths, read_json, write_json


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


async def _name_map(user_ids: list[str]) -> dict[str, str]:
    """Batch-resolve user_id → display name via the users_index SQLite cache.
    Missing ids fall back to the id itself so the UI never blanks out."""
    ids = [u for u in set(user_ids) if u]
    if not ids:
        return {}
    db = get_index_db()
    rows = await db.fetchall(
        f"SELECT id, COALESCE(name, email, id) AS name FROM users_index "
        f"WHERE id IN ({','.join('?' for _ in ids)})",
        ids,
    )
    return {r["id"]: r["name"] for r in rows}


async def _enrich(items: list[dict]) -> list[dict]:
    names = await _name_map([c.get("created_by") or "" for c in items])
    for c in items:
        uid = c.get("created_by") or ""
        c["created_by_name"] = names.get(uid) or uid or "未知"
    return items


async def list_conversations(*, task_id: str) -> list[dict]:
    paths = get_paths()
    raw = read_json(paths.task_conversations_index(task_id), default=[]) or []
    return await _enrich(list(raw))


async def create_conversation(*, task_id: str, created_by: str, title: str | None = None) -> dict:
    paths = get_paths()
    cid = _new_id()
    now = _now()
    entry = {
        "id": cid,
        "title": title or "新对话",
        "created_by": created_by,
        "created_at": now,
        "last_message_at": now,
        "message_count": 0,
    }
    idx_path = paths.task_conversations_index(task_id)
    with file_transaction([idx_path]) as tx:
        idx = tx.read_json(idx_path, default=[])
        idx.append(entry)
        tx.write_json(idx_path, idx)
    # Ensure conversation jsonl parent exists
    paths.task_conversation(task_id, cid).parent.mkdir(parents=True, exist_ok=True)
    # 回填创建者名，前端乐观更新也能直接展示
    names = await _name_map([created_by])
    entry["created_by_name"] = names.get(created_by) or created_by or "未知"
    return entry


async def rename_conversation(*, task_id: str, conv_id: str, title: str) -> dict:
    paths = get_paths()
    idx_path = paths.task_conversations_index(task_id)
    with file_transaction([idx_path]) as tx:
        idx = tx.read_json(idx_path, default=[])
        for item in idx:
            if item["id"] == conv_id:
                item["title"] = title
                tx.write_json(idx_path, idx)
                return item
    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "对话不存在")


async def delete_conversation(*, task_id: str, conv_id: str) -> None:
    paths = get_paths()
    idx_path = paths.task_conversations_index(task_id)
    with file_transaction([idx_path]) as tx:
        idx = tx.read_json(idx_path, default=[])
        idx = [c for c in idx if c["id"] != conv_id]
        tx.write_json(idx_path, idx)
    jsonl = paths.task_conversation(task_id, conv_id)
    if jsonl.exists():
        jsonl.unlink()
    lock = paths.task_conversation_lock(task_id, conv_id)
    if lock.exists():
        lock.unlink()


async def get_or_create_default(*, task_id: str, created_by: str) -> dict:
    items = await list_conversations(task_id=task_id)
    if items:
        items.sort(key=lambda c: c.get("last_message_at") or "", reverse=True)
        return items[0]
    return await create_conversation(task_id=task_id, created_by=created_by, title="默认对话")


async def touch_last_message(*, task_id: str, conv_id: str) -> None:
    """Bump last_message_at + message_count. Call after each successful message write."""
    paths = get_paths()
    idx_path = paths.task_conversations_index(task_id)
    with file_transaction([idx_path]) as tx:
        idx = tx.read_json(idx_path, default=[])
        for item in idx:
            if item["id"] == conv_id:
                item["last_message_at"] = _now()
                item["message_count"] = int(item.get("message_count", 0)) + 1
                tx.write_json(idx_path, idx)
                return


async def get_plan_mode(*, task_id: str, conv_id: str) -> dict:
    """Return {plan_mode, pending_plan_id, pending_plan_text} for a conversation.
    Defaults to plan_mode=False for old conversations without the fields."""
    paths = get_paths()
    idx = read_json(paths.task_conversations_index(task_id), default=[]) or []
    for item in idx:
        if item["id"] == conv_id:
            return {
                "plan_mode": bool(item.get("plan_mode", False)),
                "pending_plan_id": item.get("pending_plan_id"),
                "pending_plan_text": item.get("pending_plan_text"),
            }
    return {"plan_mode": False, "pending_plan_id": None, "pending_plan_text": None}


async def set_plan_mode(*, task_id: str, conv_id: str, enabled: bool) -> None:
    paths = get_paths()
    idx_path = paths.task_conversations_index(task_id)
    with file_transaction([idx_path]) as tx:
        idx = tx.read_json(idx_path, default=[])
        for item in idx:
            if item["id"] == conv_id:
                item["plan_mode"] = bool(enabled)
                if not enabled:
                    # Leaving plan mode clears any pending plan proposal.
                    item.pop("pending_plan_id", None)
                    item.pop("pending_plan_text", None)
                tx.write_json(idx_path, idx)
                return
    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "对话不存在")


async def set_pending_plan(*, task_id: str, conv_id: str, plan_id: str, plan_text: str) -> None:
    """Record that the agent has submitted a plan via exit_plan_mode. The
    conversation stays in plan_mode=True until the user approves or rejects."""
    paths = get_paths()
    idx_path = paths.task_conversations_index(task_id)
    with file_transaction([idx_path]) as tx:
        idx = tx.read_json(idx_path, default=[])
        for item in idx:
            if item["id"] == conv_id:
                item["plan_mode"] = True
                item["pending_plan_id"] = plan_id
                item["pending_plan_text"] = plan_text
                tx.write_json(idx_path, idx)
                return
    raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "对话不存在")


async def clear_pending_plan(*, task_id: str, conv_id: str) -> None:
    """Wipe plan_mode + pending_plan_* after approve/reject."""
    await set_plan_mode(task_id=task_id, conv_id=conv_id, enabled=False)


@contextmanager
def acquire_inflight_lock(*, task_id: str, conv_id: str):
    """Per-cid fcntl lock, non-blocking. Raises CONVERSATION_INFLIGHT on conflict.

    Usage:
        with acquire_inflight_lock(task_id=tid, conv_id=cid):
            # call LLM, append message to jsonl
            ...
    """
    paths = get_paths()
    lock_path = paths.task_conversation_lock(task_id, conv_id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "w")
    try:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            f.close()
            raise APIError(
                409,
                ErrorCode.CONVERSATION_INFLIGHT,
                "该对话正在处理中，请稍候",
            )
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    finally:
        f.close()
