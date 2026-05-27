"""Owner-initiated collaboration invitations.

Flow:
- Owner / admin invites N users to a task → 任务侧 invites.json + 每个 invitee 的
  inbox 各 push 一条记录 + notification_svc 推消息。
- Invitee accept → collaborators.json 加成员 + user_tasks_index 加条目（让任务出现
  在 dashboard）+ notify inviter；invitee 收件箱删该条。
- Invitee decline → 仅状态变更 + notify inviter；invitee 收件箱删该条。
- Owner cancel pending invite → 更新 invites.json + 从 invitee 收件箱删除。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..core.errors import APIError, ErrorCode
from ..core.storage import file_transaction, get_paths, read_json
from . import auth_svc, notification_svc


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _new_id() -> str:
    return "inv_" + uuid.uuid4().hex


VALID_ROLES = {"viewer", "editor", "owner"}


async def invite(
    *,
    task_id: str,
    inviter_id: str,
    invitee_ids: list[str],
    role: str = "editor",
    message: str = "",
) -> dict:
    """Send invitations to one or more users. Returns {created, skipped} —
    skipped explains per-user reason (already member / already pending / self / not found)."""
    if role not in VALID_ROLES:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, f"role 必须是 {VALID_ROLES}")
    paths = get_paths()
    meta = read_json(paths.task_meta(task_id))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")

    # Resolve inviter for notification copy
    inviter = await auth_svc.load_user_by_id(inviter_id)
    inviter_name = (inviter or {}).get("name") or "协作者"

    # Dedup invitees + filter self
    seen_ids: set[str] = set()
    clean_ids: list[str] = []
    skipped: list[dict] = []
    for uid in invitee_ids:
        uid = (uid or "").strip()
        if not uid or uid in seen_ids:
            continue
        seen_ids.add(uid)
        if uid == inviter_id:
            skipped.append({"user_id": uid, "reason": "不能邀请自己"})
            continue
        clean_ids.append(uid)

    # Existing collaborators — skip
    collabs = read_json(paths.task_collaborators(task_id), default=[]) or []
    active_member_ids = {
        c.get("user_id") for c in collabs if c.get("status") == "active"
    }
    if meta.get("owner_id"):
        active_member_ids.add(meta["owner_id"])

    inv_path = paths.task_invites(task_id)
    created: list[dict] = []
    inbox_appends: list[tuple[str, dict]] = []  # (invitee_id, inbox entry)
    notifs: list[tuple[str, dict]] = []  # (invitee_id, notification kwargs)

    with file_transaction([inv_path]) as tx:
        invites = tx.read_json(inv_path, default=[])
        pending_set = {
            i.get("invitee_id")
            for i in invites
            if i.get("status") == "pending"
        }
        for uid in clean_ids:
            if uid in active_member_ids:
                skipped.append({"user_id": uid, "reason": "已是协作者"})
                continue
            if uid in pending_set:
                skipped.append({"user_id": uid, "reason": "已邀请，待处理"})
                continue
            target_user = await auth_svc.load_user_by_id(uid)
            if not target_user:
                skipped.append({"user_id": uid, "reason": "用户不存在"})
                continue
            inv = {
                "id": _new_id(),
                "task_id": task_id,
                "inviter_id": inviter_id,
                "inviter_name": inviter_name,
                "invitee_id": uid,
                "invitee_name": target_user.get("name") or "",
                "role": role,
                "message": (message or "").strip()[:500],
                "status": "pending",
                "created_at": _now(),
                "responded_at": None,
                "decline_reason": None,
            }
            invites.append(inv)
            created.append(inv)
            pending_set.add(uid)
            # Inbox: 给被邀请人留一份去重 / 详情读取
            inbox_appends.append((
                uid,
                {
                    "invite_id": inv["id"],
                    "task_id": task_id,
                    "task_name": meta.get("name", ""),
                    "task_paradigm": meta.get("paradigm", ""),
                    "inviter_id": inviter_id,
                    "inviter_name": inviter_name,
                    "role": role,
                    "message": inv["message"],
                    "created_at": inv["created_at"],
                },
            ))
            # 桌面通知（kind=collaboration）
            notifs.append((
                uid,
                dict(
                    kind="collaboration",
                    title=f"{inviter_name} 邀请你协作",
                    body=f"任务「{meta.get('name','')}」 · 角色：{role}"
                    + (f" · 留言：{inv['message']}" if inv["message"] else ""),
                    action_url=f"/workspace/{task_id}",
                ),
            ))
        tx.write_json(inv_path, invites)

    # Inbox writes — 单文件锁逐条写，避免阻塞 invites 主锁
    for uid, entry in inbox_appends:
        inbox_path = paths.user_invites_pending(uid)
        with file_transaction([inbox_path]) as tx2:
            arr = tx2.read_json(inbox_path, default=[])
            arr.append(entry)
            tx2.write_json(inbox_path, arr)

    # Notifications best-effort
    for uid, kw in notifs:
        try:
            await notification_svc.add_notification(uid, **kw)
        except Exception:
            pass

    return {"created": created, "skipped": skipped}


async def list_for_task(*, task_id: str, status: str | None = None) -> list[dict]:
    paths = get_paths()
    invites = read_json(paths.task_invites(task_id), default=[]) or []
    if status:
        invites = [i for i in invites if i.get("status") == status]
    invites.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return invites


async def list_for_user(*, user_id: str) -> list[dict]:
    """用户的待处理收件箱。"""
    paths = get_paths()
    arr = read_json(paths.user_invites_pending(user_id), default=[]) or []
    arr.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return arr


async def cancel(*, task_id: str, invite_id: str, operator_id: str) -> dict:
    paths = get_paths()
    inv_path = paths.task_invites(task_id)
    invitee_id: str | None = None
    inviter_name = ""
    task_name = ""
    with file_transaction([inv_path]) as tx:
        invites = tx.read_json(inv_path, default=[])
        target = next((i for i in invites if i.get("id") == invite_id), None)
        if not target:
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "邀请不存在")
        if target.get("status") != "pending":
            raise APIError(409, ErrorCode.VALIDATION_ERROR, "邀请已处理，无法撤回")
        target["status"] = "cancelled"
        target["responded_at"] = _now()
        invitee_id = target.get("invitee_id")
        inviter_name = target.get("inviter_name") or ""
        meta = read_json(paths.task_meta(task_id)) or {}
        task_name = meta.get("name", "")
        tx.write_json(inv_path, invites)

    if invitee_id:
        inbox_path = paths.user_invites_pending(invitee_id)
        with file_transaction([inbox_path]) as tx2:
            arr = tx2.read_json(inbox_path, default=[])
            arr = [x for x in arr if x.get("invite_id") != invite_id]
            tx2.write_json(inbox_path, arr)
        try:
            await notification_svc.add_notification(
                invitee_id,
                kind="collaboration",
                title=f"{inviter_name or '邀请人'} 撤回了协作邀请",
                body=f"任务「{task_name}」 邀请已撤回",
                action_url=None,
            )
        except Exception:
            pass
    return {"id": invite_id, "status": "cancelled"}


async def respond(
    *, invite_id: str, invitee_id: str, action: str, decline_reason: str | None = None
) -> dict:
    if action not in {"accept", "decline"}:
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "action must be accept|decline")

    paths = get_paths()
    # 用 invitee 的 inbox 找到 task_id
    inbox_path = paths.user_invites_pending(invitee_id)
    inbox = read_json(inbox_path, default=[]) or []
    entry = next((x for x in inbox if x.get("invite_id") == invite_id), None)
    if not entry:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "邀请不存在或已处理")
    task_id = entry["task_id"]

    inv_path = paths.task_invites(task_id)
    collab_path = paths.task_collaborators(task_id)
    user_idx_path = paths.user_tasks_index(invitee_id)

    inviter_id = ""
    role = "editor"
    task_name = ""
    new_status = "accepted" if action == "accept" else "declined"

    with file_transaction([inv_path, collab_path, user_idx_path]) as tx:
        invites = tx.read_json(inv_path, default=[])
        target = next((i for i in invites if i.get("id") == invite_id), None)
        if not target:
            raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "邀请不存在")
        if target.get("invitee_id") != invitee_id:
            raise APIError(403, ErrorCode.PERMISSION_DENIED, "不是你的邀请")
        if target.get("status") != "pending":
            raise APIError(409, ErrorCode.VALIDATION_ERROR, "邀请已处理")

        target["status"] = new_status
        target["responded_at"] = _now()
        if action == "decline" and decline_reason:
            target["decline_reason"] = decline_reason.strip()[:500]
        inviter_id = target.get("inviter_id", "")
        role = target.get("role", "editor")
        meta = read_json(paths.task_meta(task_id)) or {}
        task_name = meta.get("name", "")
        tx.write_json(inv_path, invites)

        if action == "accept":
            collabs = tx.read_json(collab_path, default=[])
            # 防御去重：可能历史 entries 有 inactive 残留
            existing = next((c for c in collabs if c.get("user_id") == invitee_id), None)
            if existing:
                existing["role"] = role
                existing["status"] = "active"
                existing["joined_at"] = existing.get("joined_at") or _now()
            else:
                collabs.append({
                    "user_id": invitee_id,
                    "role": role,
                    "joined_at": _now(),
                    "status": "active",
                })
            tx.write_json(collab_path, collabs)

            user_idx = tx.read_json(user_idx_path, default=[])
            if not any(e.get("task_id") == task_id for e in user_idx):
                user_idx.append({
                    "task_id": task_id,
                    "name": task_name,
                    "paradigm": meta.get("paradigm", ""),
                    "role": "collaborator",
                    "added_at": _now(),
                })
                tx.write_json(user_idx_path, user_idx)

    # Remove from invitee inbox
    with file_transaction([inbox_path]) as tx2:
        arr = tx2.read_json(inbox_path, default=[])
        arr = [x for x in arr if x.get("invite_id") != invite_id]
        tx2.write_json(inbox_path, arr)

    # Notify inviter
    invitee = await auth_svc.load_user_by_id(invitee_id)
    invitee_name = (invitee or {}).get("name") or "协作者"
    if inviter_id:
        try:
            if action == "accept":
                await notification_svc.add_notification(
                    inviter_id,
                    kind="collaboration",
                    title=f"{invitee_name} 接受了协作邀请",
                    body=f"任务「{task_name}」 现在你们可以一起协作了",
                    action_url=f"/workspace/{task_id}",
                )
            else:
                body = f"任务「{task_name}」"
                if decline_reason:
                    body += f" · 原因：{decline_reason}"
                await notification_svc.add_notification(
                    inviter_id,
                    kind="collaboration",
                    title=f"{invitee_name} 拒绝了协作邀请",
                    body=body,
                    action_url=f"/workspace/{task_id}",
                )
        except Exception:
            pass

    return {"id": invite_id, "status": new_status, "task_id": task_id}
