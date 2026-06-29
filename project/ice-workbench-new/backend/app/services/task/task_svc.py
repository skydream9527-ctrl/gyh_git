"""Task service. Implements G3 file-first dual-write."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.services.agent import agent_snapshot_svc

from ...core.errors import APIError, ErrorCode
from ...core.storage import (
    append_jsonl,
    file_transaction,
    get_index_db,
    get_paths,
    read_json,
    read_jsonl,
    write_json,
)
from . import task_intent_svc


def _discover_default_skill_ids() -> list[str]:
    """枚举 skills/ 下所有 agentic skill 目录（含 SKILL.md 或 skill.json）。
    新建任务未显式指定 skill_ids 时默认全量注入；新增/移除 skill 自动同步。
    """
    root = get_paths().skills
    if not root.exists():
        return []
    out: list[str] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "SKILL.md").exists() or (d / "skill.json").exists():
            out.append(d.name)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


_TASK_STATUSES = {"active", "running", "paused", "failed", "archived"}
_TASK_VISIBILITIES = {"private", "public"}


async def create_task(
    *,
    name: str,
    paradigm: str,
    owner_id: str,
    agent_id: str | None = None,
    description: str | None = None,
    initial_prompt: str | None = None,
    skill_ids: list[str] | None = None,
    visibility: str = "private",
) -> dict:
    paths = get_paths()
    db = get_index_db()
    tid = _new_id()
    cid = _new_id()
    effective_agent_id, intent = task_intent_svc.choose_agent_for_task(
        requested_agent_id=agent_id,
        name=name,
        description=description,
        initial_prompt=initial_prompt,
    )
    # 未指定 skill_ids 或传空数组 → 优先使用 Agent 声明的 skills（agent.json.skills），
    # 若 Agent 未声明任何 skill 则回退到全量注入 skills/ 下的 agentic skill。
    # 显式给定非空数组按用户意图执行。
    if skill_ids:
        effective_skills = list(skill_ids)
    else:
        from app.services.agent import agents_svc

        agent_declared_skills = (
            (agents_svc.get_agent(effective_agent_id) or {}).get("skills") or []
            if effective_agent_id
            else []
        )
        if agent_declared_skills:
            effective_skills = list(agent_declared_skills)
        else:
            effective_skills = _discover_default_skill_ids()
    meta = {
        "id": tid,
        "name": name,
        "paradigm": paradigm,
        "agent_id": effective_agent_id,
        "owner_id": owner_id,
        "description": description,
        "initial_prompt": initial_prompt,
        "skill_ids": effective_skills,
        "intent": intent.as_dict(),
        "visibility": visibility,
        "publish_status": "draft",
        "status": "active",
        "file_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    # 新任务默认模型固定为 xiaomi/mimo-v2.5-pro；admin 在系统配置里禁用了它再回退
    # 到 gateway 通用默认（resolve_model(None)），避免新任务一上来就拿到 503。
    from app.services.admin import sysconfig_svc
    from app.services.llm import llm_gateway

    DEFAULT_TASK_MODEL = "xiaomi/mimo-v2.5-pro"
    enabled_ids = {
        m["id"]
        for m in (sysconfig_svc.get_llm_config().get("models") or [])
        if m.get("enabled", True)
    }
    chosen_model = (
        DEFAULT_TASK_MODEL
        if DEFAULT_TASK_MODEL in enabled_ids
        else llm_gateway.resolve_model(None)
    )
    workspace = {
        "current_conversation_id": cid,
        "model": chosen_model,
        "context_size": 20,
    }
    paths_to_lock = [paths.task_meta(tid), paths.user_tasks_index(owner_id)]
    with file_transaction(paths_to_lock) as tx:
        tx.makedirs(
            [
                paths.task_dir(tid) / "conversations",
                paths.task_dir(tid) / "tool_calls",
                paths.task_files_input(tid),
                paths.task_files_output(tid),
                paths.task_files_uploaded(tid),
                paths.task_files_meta(tid),
            ]
        )
        tx.write_json(paths.task_meta(tid), meta)
        tx.write_json(paths.task_workspace(tid), workspace)
        # Seed multi-conversation index with the default conversation so it
        # surfaces in the right-panel 对话 list from task creation, not after
        # the first WS message. Shape must match conversation_svc entries.
        tx.write_json(
            paths.task_conversations_index(tid),
            [
                {
                    "id": cid,
                    "title": "默认对话",
                    "created_by": owner_id,
                    "created_at": _now(),
                    "last_message_at": _now(),
                    "message_count": 0,
                }
            ],
        )
        tx.write_json(
            paths.task_collaborators(tid),
            [{"user_id": owner_id, "role": "owner", "joined_at": _now(), "status": "active"}],
        )
        tx.write_json(paths.task_experience_cards(tid), [])

        # C3 snapshot (Task 5): agent + skills + snapshot.json
        tx.makedirs([
            paths.task_agent_prompt_dir(tid),
            paths.task_skills_dir(tid),
            paths.task_files_imported(tid),
            paths.task_files_imported(tid) / ".meta",
        ])
        # Agent files are plain shutil copies (not transactional) because they
        # live outside the tx's managed paths; the tx still holds the meta lock.
        agent_snapshot_svc.snapshot_agent_into_task(task_id=tid, agent_id=effective_agent_id)
        agent_snapshot_svc.snapshot_skills_into_task(task_id=tid, skill_ids=effective_skills)
        snap = {
            "mode": "live",
            "agent_source_version": agent_snapshot_svc.compute_agent_version(effective_agent_id) if effective_agent_id else None,
            "frozen_at": None,
            "frozen_by": None,
            "last_manual_update_at": None,
            "last_manual_update_by": None,
        }
        tx.write_json(paths.task_snapshot(tid), snap)

        user_index = tx.read_json(paths.user_tasks_index(owner_id), default=[])
        user_index.append(
            {"task_id": tid, "name": name, "paradigm": paradigm, "role": "owner", "added_at": _now()}
        )
        tx.write_json(paths.user_tasks_index(owner_id), user_index)

    # cache index update happens after fs commit
    await db.upsert(
        "tasks_index",
        {
            "id": tid,
            "owner_id": owner_id,
            "name": name,
            "paradigm": paradigm,
            "agent_id": effective_agent_id,
            "status": "active",
            "visibility": visibility,
            "publish_status": "draft",
            "file_count": 0,
            "last_message_preview": None,
            "updated_at": meta["updated_at"],
            "created_at": meta["created_at"],
        },
    )
    await db.upsert(
        "conversations_index",
        {
            "id": cid,
            "task_id": tid,
            "title": "default",
            "created_at": meta["created_at"],
            "updated_at": meta["updated_at"],
        },
    )
    return meta


async def list_user_tasks(user_id: str, *, limit: int = 30) -> list[dict]:
    db = get_index_db()
    rows = await db.fetchall(
        "SELECT * FROM tasks_index WHERE owner_id = ? ORDER BY updated_at DESC LIMIT ?",
        [user_id, limit],
    )
    seen = {r["id"] for r in rows}
    out: list[dict] = []
    for r in rows:
        meta = read_json(get_paths().task_meta(r["id"]))
        if meta:
            meta["role"] = "owner"
            out.append(meta)

    paths = get_paths()
    user_index = read_json(paths.user_tasks_index(user_id), default=[]) or []
    for entry in user_index:
        tid = entry.get("task_id")
        if not tid or tid in seen:
            continue
        meta = read_json(paths.task_meta(tid))
        if meta and meta.get("owner_id") != user_id:
            meta["role"] = "collaborator"
            out.append(meta)
            seen.add(tid)
    out.sort(key=lambda m: m.get("updated_at") or "", reverse=True)
    return out[:limit]


async def list_public_tasks(limit: int = 50) -> list[dict]:
    db = get_index_db()
    rows = await db.fetchall(
        "SELECT * FROM tasks_index WHERE visibility = 'public' AND publish_status = 'published' ORDER BY updated_at DESC LIMIT ?",
        [limit],
    )
    out: list[dict] = []
    for r in rows:
        meta = read_json(get_paths().task_meta(r["id"]))
        if meta:
            out.append(meta)
    # Batch-resolve owner names so the dashboard 公共任务 cards can display
    # who shared each task. One SQL with `IN (?, ?, …)` keeps the per-row N+1
    # cost out of the hot path even with 50 tasks.
    owner_ids = sorted({m.get("owner_id") for m in out if m.get("owner_id")})
    if owner_ids:
        placeholders = ",".join("?" * len(owner_ids))
        urows = await db.fetchall(
            f"SELECT id, name FROM users_index WHERE id IN ({placeholders})",
            list(owner_ids),
        )
        name_by_id = {u["id"]: u["name"] for u in urows}
        for m in out:
            m["owner_name"] = name_by_id.get(m.get("owner_id")) or ""
    return out


async def get_task(task_id: str, user_id: str, *, is_admin: bool = False) -> dict:
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    collaborators = read_json(paths.task_collaborators(task_id), default=[])
    if not is_admin and meta.get("owner_id") != user_id and meta.get("visibility") != "public":
        if not any(c["user_id"] == user_id and c.get("status") == "active" for c in collaborators):
            # Cross-cutting admin bypass: admin / super_admin can read any task
            # even when the caller forgot to pass is_admin=True. Keeps every
            # /tasks/* and /files/task/* route admin-aware without threading
            # the flag through 15+ call sites.
            from app.services.auth import auth_svc

            u = await auth_svc.load_user_by_id(user_id)
            if not u or u.get("auth_role") not in ("admin", "super_admin"):
                raise APIError(403, ErrorCode.PERMISSION_DENIED, "无权访问此任务")
            # Caller didn't pass is_admin but user is global admin — promote so
            # the derived role below comes back as "admin", not None.
            is_admin = True
    workspace = read_json(paths.task_workspace(task_id), default={})
    from app.services.agent import agent_snapshot_svc
    snap = read_json(paths.task_snapshot(task_id)) or {
        "mode": "live",
        "agent_source_version": None,
        "frozen_at": None,
        "frozen_by": None,
        "last_manual_update_at": None,
        "last_manual_update_by": None,
    }
    agent_update_available = False
    if meta.get("visibility") == "public":
        aid = meta.get("agent_id")
        if aid:
            current_version = agent_snapshot_svc.compute_agent_version(aid)
            if current_version and current_version != snap.get("agent_source_version"):
                agent_update_available = True

    # 派生当前调用者在该任务上的角色，回给前端。前端不再自己算，避免和后端
    # derive_task_role 漏档导致 viewer 拿到编辑态 UI、消息发到后端被 WS 拒掉
    # 的情况。owner / editor / viewer / admin 之外（理论上不可达，因为前面
    # 的访问校验已经放行）落到 None。
    from ...core.deps import derive_task_role

    role = derive_task_role(meta, collaborators, user_id=user_id, is_admin=is_admin)
    return {
        **meta,
        "workspace": workspace,
        "collaborators": collaborators,
        "role": role.value if role is not None else None,
        "snapshot": snap,
        "agent_update_available": agent_update_available,
    }


async def update_skills(
    task_id: str, user_id: str, skill_ids: list[str], *, is_admin: bool = False
) -> dict:
    """Update a task's bound skills (add / remove). Only owner or global admin
    can modify. Re-snapshots every listed skill into the task folder so the
    agent-runtime picks it up on next turn without restart.
    """
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    if not is_admin and meta.get("owner_id") != user_id:
        # allow global admin / super_admin
        from app.services.auth import auth_svc
        u = await auth_svc.load_user_by_id(user_id)
        if not u or u.get("auth_role") not in ("admin", "super_admin"):
            raise APIError(403, ErrorCode.PERMISSION_DENIED, "仅任务创建者或管理员可修改 skill")

    # Dedup + sanitize
    seen: set[str] = set()
    clean: list[str] = []
    for sid in skill_ids or []:
        sid = (sid or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        clean.append(sid)

    meta["skill_ids"] = clean
    meta["updated_at"] = _now()
    with file_transaction([paths.task_meta(task_id)]) as tx:
        tx.write_json(paths.task_meta(task_id), meta)
    # Re-snapshot: wipes old skill files then writes fresh ones
    skills_dir = paths.task_skills_dir(task_id)
    if skills_dir.exists():
        import shutil
        shutil.rmtree(skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)
    agent_snapshot_svc.snapshot_skills_into_task(task_id=task_id, skill_ids=clean)

    db = get_index_db()
    await db.execute(
        "UPDATE tasks_index SET updated_at = ? WHERE id = ?",
        [meta["updated_at"], task_id],
    )
    return {"task_id": task_id, "skill_ids": clean}


async def update_task(
    task_id: str,
    user_id: str,
    patch: dict,
    *,
    is_admin: bool = False,
    allow_visibility: bool = False,
) -> dict:
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    if not is_admin and meta.get("owner_id") != user_id:
        collaborators = read_json(paths.task_collaborators(task_id), default=[]) or []
        if not any(
            c.get("user_id") == user_id and c.get("status") == "active" and c.get("role") == "editor"
            for c in collaborators
        ):
            raise APIError(403, ErrorCode.PERMISSION_DENIED, "当前身份无此权限")

    updates: dict = {}
    if "name" in patch and patch.get("name") is not None:
        name = str(patch.get("name") or "").strip()
        if not name:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "任务名称不能为空")
        if len(name) > 120:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "任务名称过长")
        updates["name"] = name
    if "description" in patch:
        desc = patch.get("description")
        updates["description"] = str(desc) if desc is not None else None
    if "status" in patch and patch.get("status") is not None:
        status = str(patch.get("status") or "").strip()
        if status not in _TASK_STATUSES:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "任务状态无效")
        updates["status"] = status
    if "visibility" in patch and patch.get("visibility") is not None:
        if not allow_visibility and not is_admin and meta.get("owner_id") != user_id:
            raise APIError(403, ErrorCode.PERMISSION_DENIED, "仅任务创建者可修改可见性")
        visibility = str(patch.get("visibility") or "").strip()
        if visibility not in _TASK_VISIBILITIES:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "任务可见性无效")
        updates["visibility"] = visibility

    if not updates:
        return await get_task(task_id, user_id, is_admin=is_admin)

    meta.update(updates)
    meta["updated_at"] = _now()
    locks = [paths.task_meta(task_id), paths.user_tasks_index(meta["owner_id"])]
    with file_transaction(locks) as tx:
        tx.write_json(paths.task_meta(task_id), meta)
        if "name" in updates:
            user_index = tx.read_json(paths.user_tasks_index(meta["owner_id"]), default=[]) or []
            for entry in user_index:
                if entry.get("task_id") == task_id:
                    entry["name"] = updates["name"]
            tx.write_json(paths.user_tasks_index(meta["owner_id"]), user_index)

    db = get_index_db()
    await db.execute(
        """
        UPDATE tasks_index
        SET name = COALESCE(?, name),
            status = COALESCE(?, status),
            visibility = COALESCE(?, visibility),
            updated_at = ?
        WHERE id = ?
        """,
        [
            updates.get("name"),
            updates.get("status"),
            updates.get("visibility"),
            meta["updated_at"],
            task_id,
        ],
    )
    return await get_task(task_id, user_id, is_admin=is_admin)


async def set_task_status(task_id: str, status: str, *, only_if: set[str] | None = None) -> dict | None:
    if status not in _TASK_STATUSES:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "任务状态无效")
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        return None
    if only_if is not None and meta.get("status") not in only_if:
        return meta
    meta["status"] = status
    meta["updated_at"] = _now()
    write_json(paths.task_meta(task_id), meta)
    await get_index_db().execute(
        "UPDATE tasks_index SET status = ?, updated_at = ? WHERE id = ?",
        [status, meta["updated_at"], task_id],
    )
    return meta


def append_run_event(task_id: str, conv_id: str, event: dict) -> None:
    append_jsonl(get_paths().task_run_events(task_id, conv_id), event)


def list_run_events(task_id: str, conv_id: str, *, limit: int = 80) -> list[dict]:
    rows = read_jsonl(get_paths().task_run_events(task_id, conv_id))
    return rows[-limit:]


async def delete_task(task_id: str, user_id: str, *, is_admin: bool = False) -> None:
    """Hard-delete a task: filesystem dir + index rows + user index entry.

    Only the owner (or an admin invoking from the admin surface) can delete.
    Files / conversations / tool_calls / experience cards under the task are
    wiped from disk; index tables are scrubbed.
    """
    import shutil

    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    if not is_admin and meta.get("owner_id") != user_id:
        raise APIError(403, ErrorCode.PERMISSION_DENIED, "仅创建者可删除任务")

    owner_id = meta["owner_id"]
    user_index_path = paths.user_tasks_index(owner_id)
    paths_to_lock = [paths.task_meta(task_id), user_index_path]
    with file_transaction(paths_to_lock) as tx:
        items = tx.read_json(user_index_path, default=[]) or []
        items = [it for it in items if it.get("task_id") != task_id]
        tx.write_json(user_index_path, items)

    task_dir = paths.task_dir(task_id)
    if task_dir.exists():
        shutil.rmtree(task_dir, ignore_errors=True)

    db = get_index_db()
    for table, col in (
        ("tasks_index", "id"),
        ("files_index", "task_id"),
        ("messages_index", "task_id"),
        ("conversations_index", "task_id"),
        ("sql_audit", "task_id"),
        ("llm_usage", "task_id"),
    ):
        try:
            await db.execute(f"DELETE FROM {table} WHERE {col} = ?", [task_id])
        except Exception:
            pass


async def touch_task(task_id: str, *, last_message_preview: str | None = None) -> None:
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        return
    meta["updated_at"] = _now()
    if last_message_preview is not None:
        meta["last_message_preview"] = last_message_preview[:120]
    write_json(paths.task_meta(task_id), meta)
    db = get_index_db()
    await db.execute(
        "UPDATE tasks_index SET updated_at = ?, last_message_preview = COALESCE(?, last_message_preview) WHERE id = ?",
        [meta["updated_at"], meta.get("last_message_preview"), task_id],
    )


async def get_or_create_default_conversation(task_id: str) -> str:
    paths = get_paths()
    workspace = read_json(paths.task_workspace(task_id), default={})
    cid = workspace.get("current_conversation_id")
    # 同步到右栏多对话列表（老任务可能只在 workspace.json 里有，列表还是空）
    conv_idx_path = paths.task_conversations_index(task_id)
    conv_idx = read_json(conv_idx_path, default=[]) or []
    if cid:
        if not any(c.get("id") == cid for c in conv_idx):
            owner = read_json(paths.task_meta(task_id), default={}).get("owner_id")
            conv_idx.append({
                "id": cid,
                "title": "默认对话",
                "created_by": owner or "",
                "created_at": _now(),
                "last_message_at": _now(),
                "message_count": 0,
            })
            write_json(conv_idx_path, conv_idx)
        return cid
    cid = _new_id()
    workspace["current_conversation_id"] = cid
    write_json(paths.task_workspace(task_id), workspace)
    owner = read_json(paths.task_meta(task_id), default={}).get("owner_id")
    conv_idx.append({
        "id": cid,
        "title": "默认对话",
        "created_by": owner or "",
        "created_at": _now(),
        "last_message_at": _now(),
        "message_count": 0,
    })
    write_json(conv_idx_path, conv_idx)
    db = get_index_db()
    await db.upsert(
        "conversations_index",
        {"id": cid, "task_id": task_id, "title": "default", "created_at": _now(), "updated_at": _now()},
    )
    return cid


def load_conversation_messages(task_id: str, conv_id: str) -> list[dict]:
    from ...core.storage import read_jsonl

    paths = get_paths()
    messages = read_jsonl(paths.task_conversation(task_id, conv_id))
    tool_results: dict[str, dict] = {}
    for rec in read_jsonl(paths.task_tool_calls(task_id, conv_id)):
        tid = rec.get("id")
        if tid:
            tool_results[tid] = rec
    if not tool_results:
        return messages

    for msg in messages:
        if msg.get("role") != "assistant":
            continue
        merged = []
        for tu in msg.get("tool_uses") or []:
            tid = tu.get("id")
            rec = tool_results.get(tid)
            if not rec:
                merged.append(tu)
                continue
            next_tu = dict(tu)
            next_tu["status"] = rec.get("status")
            next_tu["success"] = rec.get("success")
            if rec.get("result") is not None:
                next_tu["result"] = rec.get("result")
            if rec.get("error") is not None:
                next_tu["error"] = rec.get("error")
            merged.append(next_tu)
        if merged:
            msg["tool_uses"] = merged
    return messages


def load_conversation_messages_page(
    task_id: str,
    conv_id: str,
    *,
    limit: int = 80,
    before: int | None = None,
) -> dict:
    """Return an oldest-to-newest page from a conversation.

    `before` is an exclusive message index in the full JSONL array. Omitting it
    returns the latest page. The implementation still reads JSONL as the source
    of truth, but keeps large histories off the wire and out of React's render
    tree on initial load.
    """
    limit = max(1, min(int(limit or 80), 200))
    all_messages = load_conversation_messages(task_id, conv_id)
    total = len(all_messages)
    end = total if before is None else max(0, min(int(before), total))
    start = max(0, end - limit)
    return {
        "messages": all_messages[start:end],
        "total": total,
        "next_before": start if start > 0 else None,
        "has_more": start > 0,
    }
