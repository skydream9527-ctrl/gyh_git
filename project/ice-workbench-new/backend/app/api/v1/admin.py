"""Admin endpoints — overview/users/agents/audit. Require admin role."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.deps import get_current_user, require_admin, require_super_admin
from ...core.errors import APIError, ErrorCode, ok
from ...core.storage import file_transaction, get_index_db, get_paths, read_json, write_json
from ...services import admin_svc, agents_svc, task_svc

router = APIRouter()


# ---- overview ----


@router.get("/overview/stats")
async def overview_stats(
    days: int = Query(30, ge=1, le=365),
    _: dict = Depends(require_admin),
):
    db = get_index_db()
    user_row = await db.fetchone("SELECT COUNT(*) AS c FROM users_index")
    task_row = await db.fetchone("SELECT COUNT(*) AS c FROM tasks_index")
    msg_row = await db.fetchone("SELECT COUNT(*) AS c FROM messages_index")
    return ok(
        {
            "users": int((user_row or {}).get("c") or 0),
            "tasks": int((task_row or {}).get("c") or 0),
            "messages": int((msg_row or {}).get("c") or 0),
            "days": days,
        }
    )


@router.get("/overview/alerts")
async def overview_alerts(_: dict = Depends(require_admin)):
    """Pending review counters (D104) + LLM monthly-budget state."""
    from ...services import experience_card_svc, usage_svc

    paths = get_paths()
    counts: dict = {
        "experience_cards": 0,
        "public_tasks": 0,
        "templates": 0,
        "scheduled_failed": 0,
        "pending_users": 0,
        # Budget alert — exposed so AdminOverview can render a banner. The
        # actual spend / ratio / budget are attached below under `budget` so
        # we don't have to re-query /admin/usage to render a meaningful line.
        "budget_alert": None,
        "budget": None,
    }
    db = get_index_db()
    await experience_card_svc.ensure_index()
    row = await db.fetchone(
        "SELECT COUNT(*) AS c FROM experience_cards_index WHERE status = 'draft'"
    )
    counts["experience_cards"] = int((row or {}).get("c") or 0)
    row = await db.fetchone(
        "SELECT COUNT(*) AS c FROM users_index WHERE status = 'pending'"
    )
    counts["pending_users"] = int((row or {}).get("c") or 0)
    tdir = paths.tasks / ".templates"
    if tdir.exists():
        for d in tdir.iterdir():
            if not d.is_dir():
                continue
            t = read_json(d / "template.json")
            if t and t.get("visibility") == "public" and t.get("status") == "draft":
                counts["templates"] += 1
    row = await db.fetchone(
        "SELECT COUNT(*) AS c FROM tasks_index WHERE visibility = 'public' AND publish_status = 'pending'"
    )
    counts["public_tasks"] = int((row or {}).get("c") or 0)
    # Budget: only surface when something is worth alerting on (warning /
    # exceeded). At `ok` we leave budget_alert=None so the UI doesn't show
    # a banner during normal operation.
    try:
        summary = await usage_svc.month_summary()
        counts["budget"] = {
            "month": summary["month"],
            "cost_usd": summary["cost_usd"],
            "budget_usd": summary["budget_usd"],
            "used_ratio": summary["budget_used_ratio"],
            "state": summary["budget_state"],
        }
        if summary["budget_state"] in ("warning", "exceeded"):
            counts["budget_alert"] = summary["budget_state"]
    except Exception:
        # Never let a usage-query failure break the overview page.
        pass
    return ok(counts)


@router.get("/overview/recent-users")
async def recent_users(_: dict = Depends(require_admin), limit: int = 10):
    db = get_index_db()
    rows = await db.fetchall(
        "SELECT id, email, name, auth_role, created_at FROM users_index ORDER BY created_at DESC LIMIT ?",
        [limit],
    )
    return ok({"items": rows})


@router.get("/overview/agent-ranking")
async def agent_ranking(_: dict = Depends(require_admin), days: int = 30):
    return ok({"items": admin_svc.agent_ranking(days=days)})


# ---- users ----


@router.get("/users")
async def list_users(
    q: str | None = Query(None),
    role: str | None = Query(None),
    status: str | None = Query(None),
    _: dict = Depends(require_admin),
):
    items = await admin_svc.list_users(q=q, role=role, status=status)
    return ok({"items": items, "total": len(items)})


@router.post("/users")
async def create_user(body: dict, op: dict = Depends(require_admin)):
    user = await admin_svc.create_user(
        operator=op,
        email=body["email"],
        name=body.get("name", body["email"]),
        auth_role=body.get("auth_role", "user"),
        password=body.get("password"),
        team=body.get("team"),
        title=body.get("title"),
    )
    return ok(user)


@router.patch("/users/{uid}")
async def update_user(uid: str, body: dict, op: dict = Depends(require_admin)):
    return ok(await admin_svc.update_user(operator=op, uid=uid, patch=body))


@router.post("/users/{uid}/review")
async def review_registration(
    uid: str, body: dict, op: dict = Depends(require_admin)
):
    """Approve or reject a pending registration.

    Body: `{"decision": "approved" | "rejected", "reason": "<optional when rejected>"}`
    Approved → status flips to active so the user can log in.
    Rejected → status flips to rejected and the reason is surfaced at login.
    """
    decision = (body.get("decision") or "").strip()
    reason = body.get("reason")
    profile = await admin_svc.review_registration(
        operator=op, uid=uid, decision=decision, reason=reason
    )
    return ok(
        {
            "id": profile["id"],
            "status": profile["status"],
            "reviewed_by": profile.get("reviewed_by"),
            "reviewed_at": profile.get("reviewed_at"),
            "reject_reason": profile.get("reject_reason"),
        }
    )


@router.delete("/users/{uid}")
async def delete_user(uid: str, op: dict = Depends(require_super_admin)):
    await admin_svc.delete_user(operator=op, uid=uid)
    return ok({"deleted": True})


# ---- per-user tasks (admin) ----


@router.get("/users/{uid}/tasks")
async def admin_list_user_tasks(
    uid: str,
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(require_admin),
):
    """List a user's tasks (owner or active collaborator). Returns task meta
    plus role hint so the admin UI can show ownership context."""
    paths = get_paths()
    if not read_json(paths.user_profile(uid)):
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "用户不存在")
    items = await task_svc.list_user_tasks(uid, limit=limit)
    return ok({"items": items, "total": len(items)})


_TASK_META_EDITABLE = {
    "name",
    "description",
    "visibility",
    "publish_status",
    "status",
    "agent_id",
    "initial_prompt",
}


@router.patch("/tasks/{tid}")
async def admin_update_task(tid: str, body: dict, op: dict = Depends(require_admin)):
    """Edit a task's meta on behalf of any user. Allowed keys:
    name / description / visibility / publish_status / status / agent_id /
    initial_prompt. Other fields are ignored. Audited as `admin_update_task`."""
    paths = get_paths()
    meta_path = paths.task_meta(tid)
    meta = read_json(meta_path)
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    diff = {"before": {}, "after": {}}
    for k in _TASK_META_EDITABLE:
        if k not in body:
            continue
        new_val = body[k]
        if new_val == meta.get(k):
            continue
        diff["before"][k] = meta.get(k)
        diff["after"][k] = new_val
        meta[k] = new_val
    if not diff["after"]:
        return ok(meta)
    from datetime import datetime, timezone

    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    with file_transaction([meta_path]) as tx:
        tx.write_json(meta_path, meta)

    db = get_index_db()
    await db.execute(
        "UPDATE tasks_index SET name = ?, agent_id = ?, visibility = ?, publish_status = ?, status = ?, updated_at = ? WHERE id = ?",
        [
            meta.get("name"),
            meta.get("agent_id"),
            meta.get("visibility"),
            meta.get("publish_status"),
            meta.get("status"),
            meta["updated_at"],
            tid,
        ],
    )
    await admin_svc.audit(
        admin_id=op["id"],
        action="admin_update_task",
        target_type="task",
        target_id=tid,
        diff=diff,
    )
    return ok(meta)


@router.patch("/tasks/{tid}/skills")
async def admin_update_task_skills(
    tid: str, body: dict, op: dict = Depends(require_admin)
):
    """Replace the task's bound skill_ids on behalf of any user."""
    skill_ids = body.get("skill_ids")
    if not isinstance(skill_ids, list):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "skill_ids 必须是数组")
    res = await task_svc.update_skills(tid, op["id"], skill_ids, is_admin=True)
    await admin_svc.audit(
        admin_id=op["id"],
        action="admin_update_task_skills",
        target_type="task",
        target_id=tid,
        diff={"after": {"skill_ids": res["skill_ids"]}},
    )
    return ok(res)


@router.delete("/tasks/{tid}")
async def admin_delete_task(tid: str, op: dict = Depends(require_admin)):
    """Hard-delete any user's task. Audited as `admin_delete_task`."""
    paths = get_paths()
    meta = read_json(paths.task_meta(tid))
    if not meta:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "任务不存在")
    owner_id = meta.get("owner_id") or op["id"]
    await task_svc.delete_task(tid, op["id"], is_admin=True)
    await admin_svc.audit(
        admin_id=op["id"],
        action="admin_delete_task",
        target_type="task",
        target_id=tid,
        diff={"before": {"owner_id": owner_id, "name": meta.get("name")}},
    )
    return ok({"deleted": True, "task_id": tid})


# ---- audit ----


@router.get("/audit-logs")
async def audit_logs(
    admin_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(require_admin),
):
    items = await admin_svc.list_audit_logs(admin_id=admin_id, limit=limit)
    return ok({"items": items, "total": len(items)})


# ---- agents (admin) ----


@router.get("/agents")
async def admin_list_agents(_: dict = Depends(require_admin)):
    items = agents_svc.list_agents()
    return ok({"items": items, "total": len(items)})


@router.get("/tools/builtin")
async def admin_list_builtin_tools(_: dict = Depends(require_admin)):
    """Catalog of builtin tools the admin UI can pick from for an agent's
    `tools[]` whitelist. Pulled from `BUILTIN_TOOL_SCHEMAS` so adding a new
    tool to tool_runner automatically surfaces it here."""
    from app.services.llm.tool_runner import BUILTIN_TOOL_SCHEMAS

    items = []
    for t in BUILTIN_TOOL_SCHEMAS:
        fn = t.get("function") or {}
        meta = t.get("_meta") or {}
        items.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description"),
                "display_name": meta.get("display_name") or fn.get("name"),
                "side_effect": meta.get("side_effect", "read"),
                "plan_mode_allowed": bool(meta.get("plan_mode_allowed", False)),
                "subagent_exposable": bool(meta.get("subagent_exposable", False)),
            }
        )
    return ok({"items": items, "total": len(items)})


@router.get("/agents/{aid}")
async def admin_agent_detail(aid: str, _: dict = Depends(require_admin)):
    a = agents_svc.get_agent(aid)
    if not a:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "Agent 不存在")
    a["system_prompt"] = agents_svc.get_agent_system_prompt(aid)
    return ok(a)


@router.post("/agents")
async def admin_agent_create(body: dict, op: dict = Depends(require_admin)):
    """Create a new agent — writes `agents/<id>/agent.json` + `prompt/system.md`.

    Body: `{id, name, paradigm, icon?, color?, description?, system_prompt?, publish_status?}`.
    Returns the new agent config on success. Audits `create_agent`.
    """
    cfg = agents_svc.create_agent(
        agent_id=body.get("id") or "",
        name=body.get("name") or "",
        paradigm=body.get("paradigm") or "",
        icon=body.get("icon") or "",
        color=body.get("color") or "",
        description=body.get("description") or "",
        system_prompt=body.get("system_prompt") or "",
        publish_status=body.get("publish_status") or "draft",
    )
    await admin_svc.audit(
        admin_id=op["id"],
        action="create_agent",
        target_type="agent",
        target_id=cfg["id"],
        diff={"after": cfg},
    )
    return ok(cfg)


@router.delete("/agents/{aid}")
async def admin_agent_delete(
    aid: str, force: bool = False, op: dict = Depends(require_admin)
):
    """Remove an agent. Refuses if the agent is referenced by tasks; pass
    `?force=true` to override (existing tasks still work via per-task snapshot,
    but new tasks cannot pick this agent).

    Seed agents (biz-insight etc.) are protected — they cannot be deleted
    because the seed loop would recreate them.
    """
    result = await agents_svc.delete_agent(agent_id=aid, force=force)
    await admin_svc.audit(
        admin_id=op["id"],
        action="delete_agent",
        target_type="agent",
        target_id=aid,
        diff={"force": force, "tasks_orphaned": result["tasks_orphaned"]},
    )
    return ok(result)


@router.patch("/agents/{aid}")
async def admin_agent_update(aid: str, body: dict, op: dict = Depends(require_admin)):
    cfg = agents_svc.get_agent(aid)
    if not cfg:
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, "Agent 不存在")
    diff = {"before": {}, "after": {}}
    for k in ("name", "description", "icon", "color", "publish_status", "paradigm", "prompt_layout"):
        if k in body and body[k] != cfg.get(k):
            diff["before"][k] = cfg.get(k)
            diff["after"][k] = body[k]
            cfg[k] = body[k]
    # Declarative v3 fields. Each is optional; missing = inherit defaults.
    # Validate light-touch (types only) — full validation is light here so
    # admins can experiment without a frontend round-trip.
    for arr_key in ("tools", "spawn_targets", "skills"):
        if arr_key in body:
            val = body[arr_key]
            if val is None:
                if arr_key in cfg:
                    diff["before"][arr_key] = cfg.get(arr_key)
                    diff["after"][arr_key] = None
                    cfg.pop(arr_key, None)
            elif isinstance(val, list) and all(isinstance(x, str) for x in val):
                if val != cfg.get(arr_key):
                    diff["before"][arr_key] = cfg.get(arr_key)
                    diff["after"][arr_key] = val
                    cfg[arr_key] = val
            else:
                raise APIError(400, ErrorCode.VALIDATION_ERROR, f"`{arr_key}` 必须是字符串数组或 null")
    if "model" in body:
        m = body["model"]
        if m is None or (isinstance(m, str) and not m.strip()):
            if cfg.get("model"):
                diff["before"]["model"] = cfg.get("model")
                diff["after"]["model"] = None
                cfg.pop("model", None)
        elif isinstance(m, str):
            if m != cfg.get("model"):
                diff["before"]["model"] = cfg.get("model")
                diff["after"]["model"] = m
                cfg["model"] = m
        else:
            raise APIError(400, ErrorCode.VALIDATION_ERROR, "`model` 必须是字符串或 null")
    if "features" in body:
        feats = body["features"] if isinstance(body["features"], dict) else {}
        # Whitelist keys + coerce to bool/None. Setting a key to None removes
        # the override (falls back to global env flag).
        clean: dict = {}
        for fk in ("spawn_subagent", "run_background", "todo_write", "exit_plan_mode"):
            if fk in feats and feats[fk] is not None:
                clean[fk] = bool(feats[fk])
        if clean != (cfg.get("features") or {}):
            diff["before"]["features"] = cfg.get("features") or {}
            diff["after"]["features"] = clean
            cfg["features"] = clean
    if "system_prompt" in body:
        admin_svc.update_agent_prompt(
            aid=aid,
            new_prompt=body["system_prompt"],
            operator=op,
            change_note=body.get("change_note"),
        )
        # update_agent_prompt rewrites agent.json from disk, dropping any
        # in-memory edits we made above. Re-apply features/etc. by reloading
        # and merging.
        if diff["after"]:
            from ...core.storage import write_json

            fresh = agents_svc.get_agent(aid) or {}
            for k in diff["after"]:
                fresh[k] = diff["after"][k]
            write_json(get_paths().agents / aid / "agent.json", fresh)
            cfg = fresh
    else:
        from ...core.storage import write_json

        write_json(get_paths().agents / aid / "agent.json", cfg)
    await admin_svc.audit(
        admin_id=op["id"], action="update_agent", target_type="agent", target_id=aid, diff=diff
    )
    return ok(cfg)


@router.get("/agents/{aid}/prompt-history")
async def prompt_history(aid: str, _: dict = Depends(require_admin)):
    return ok({"items": admin_svc.list_prompt_history(aid)})


@router.post("/agents/{aid}/prompt-rollback")
async def prompt_rollback(aid: str, body: dict, op: dict = Depends(require_admin)):
    cfg = admin_svc.rollback_agent_prompt(aid=aid, history_id=body["history_id"], operator=op)
    await admin_svc.audit(
        admin_id=op["id"],
        action="rollback_agent_prompt",
        target_type="agent",
        target_id=aid,
        diff={"history_id": body["history_id"]},
    )
    return ok(cfg)


@router.post("/agents/{aid}/test-chat")
async def test_chat(aid: str, body: dict, _: dict = Depends(require_admin)):
    """Sandbox: not persisted, not metered. Return synchronous text."""
    from ...core.config import get_settings
    from ...services import llm_gateway

    s = get_settings()
    if not s.llm_enabled:
        raise APIError(503, ErrorCode.LLM_KEY_MISSING, "LLM 未配置")
    sp = body.get("system_prompt") or agents_svc.get_agent_system_prompt(aid)
    msgs = body.get("messages") or [{"role": "user", "content": body.get("content", "你好")}]
    model_id = body.get("model") or llm_gateway.resolve_model(None)
    result = await llm_gateway.complete_once(
        system_prompt=sp, messages=msgs, model=model_id, max_tokens=2048
    )
    return ok({"response": result.get("text") or "", "model": result.get("model"), "usage": result.get("usage")})
