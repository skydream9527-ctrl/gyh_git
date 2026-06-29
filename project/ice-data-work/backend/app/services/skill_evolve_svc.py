"""Skill/Agent 自演进（D-13 §10.5）：候选物化 → 团队晋升（双门）→ 绑定 Agent → 版本化。

闭环：
    1) materialize_candidate：用户在「贡献为 Skill」表单确认 → 先落"个人草稿 Skill"（立即可用），
       绑定到 Agent（个人绑定）；若选"贡献给团队"，额外发起团队晋升审批（进审核中心）。
    2) promote_to_team：团队晋升强制**双门** —— 门1 沙盒 test-run 通过；门2 owner/admin 审核
       （API 层 require_member owner/admin 把关 + HITL 审批留痕）。晋升后团队绑定 Agent + 版本 +1。
    3) rollback_skill：回滚到历史版本（写新版本，不删历史）。

隔离/复用：个人草稿不泄漏他人；显式"贡献给团队"才共享（与记忆 D-06 一致）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import read_json, write_json
from app.core.storage.transaction import file_transaction
from app.services import audit_svc, hitl_svc, skill_svc


# ─────────────────── 候选物化（表单确认后）───────────────────

def materialize_candidate(task_id: str, candidate_id: str, *, decided_by: str, uid: str, bind: bool = True) -> dict:
    """把 Skill 候选物化为个人草稿（立即可用）+ 绑定 Agent；若提议 by_team 则发起团队晋升审批。"""
    cand = skill_svc.get_skill_candidate(task_id, candidate_id)
    if cand.get("status") == skill_svc.STATUS_APPROVED:
        raise APIError(409, ErrorCode.CONFLICT, "该 Skill 候选已沉淀")

    skill = skill_svc.create_user_skill(
        uid, name=cand["name"], description=cand.get("description", ""),
        runtime=cand["runtime"], code=cand["code"],
        input_schema=cand.get("input_schema"), knowledge=cand.get("knowledge", ""),
        source_task=task_id,
    )

    bound_agent = None
    if bind and cand.get("agent_id"):
        bind_to_agent(cand["agent_id"], skill["id"], uid=uid, team=False, knowledge=cand.get("knowledge", ""))
        bound_agent = cand["agent_id"]

    skill_svc.append_candidate_update(task_id, candidate_id, {
        "status": skill_svc.STATUS_APPROVED, "decided_by": decided_by,
        "skill_id": skill["id"], "materialized_scope": skill_svc.SCOPE_BY_USER,
    })
    audit_svc.record(
        actor=decided_by, action="skill_materialize", task_id=task_id,
        summary=f"沉淀个人草稿 Skill「{cand['name']}」({skill['id']})",
        detail={"skill_id": skill["id"], "bound_agent": bound_agent},
    )

    result = {
        "skill_id": skill["id"], "scope": skill_svc.SCOPE_BY_USER,
        "bound_agent": bound_agent, "immediately_usable": True, "needs_review": False,
    }

    # 提议贡献给团队 → 发起晋升审批（双门之门2：owner/admin 审核）
    if cand.get("proposed_scope") == skill_svc.SCOPE_BY_TEAM:
        appr = hitl_svc.create_approval(
            task_id, action_type="skill_promote",
            summary=f"将 Skill「{cand['name']}」贡献给团队（需沙盒 test-run 通过 + owner/admin 审核）",
            risk_level="medium", requester=decided_by,
            payload={"skill_id": skill["id"], "uid": uid, "agent_id": cand.get("agent_id", ""),
                     "candidate_id": candidate_id},
        )
        result["promotion_approval_id"] = appr["id"]
        result["needs_review"] = True
    return result


# ─────────────────── 团队晋升（双门）───────────────────

def promote_to_team(skill_id: str, *, uid: str, tid: str, decided_by: str,
                    agent_id: str = "", require_test: bool = True) -> dict:
    """个人草稿 → 团队 Skill。门1：沙盒 test-run 通过；门2：owner/admin 审核（调用方把关）。"""
    user_skill = skill_svc.get_skill(skill_id, uid=uid)
    if user_skill.get("scope") != skill_svc.SCOPE_BY_USER:
        raise APIError(400, ErrorCode.BAD_REQUEST, "仅个人草稿可晋升为团队 Skill")

    # 门1：沙盒 test-run 通过
    if require_test and not user_skill.get("test_passed"):
        raise APIError(409, ErrorCode.CONFLICT, "团队晋升前置门未过：需先沙盒 test-run 通过")

    code = skill_svc.read_skill_code(user_skill)
    now = _now_iso()
    team_skill = {
        **user_skill, "id": skill_id, "scope": skill_svc.SCOPE_BY_TEAM,
        "owner": {"tid": tid}, "version": 1,
        "promoted_from": {"uid": uid, "skill_id": skill_id},
        "created_at": now, "updated_at": now,
    }
    root = paths.skill_dir(skill_id)
    sjp = paths.skill_json(skill_id)
    with file_transaction([sjp, root / "versions" / "1" / "code.txt", root / "versions" / "1" / "meta.json"]):
        skill_svc._write_version(root, 1, code, user_skill["runtime"],
                                 user_skill.get("input_schema", []), note=f"promoted from user:{uid}")
        write_json(sjp, team_skill)

    bound_agent = None
    if agent_id:
        bind_to_agent(agent_id, skill_id, team=True, knowledge=user_skill.get("knowledge", ""))
        bound_agent = agent_id

    audit_svc.record(
        actor=decided_by, action="skill_promote",
        summary=f"Skill「{user_skill['name']}」({skill_id}) 晋升到团队 {tid}",
        detail={"skill_id": skill_id, "tid": tid, "bound_agent": bound_agent, "from_uid": uid},
    )
    return {"skill_id": skill_id, "scope": skill_svc.SCOPE_BY_TEAM, "tid": tid, "bound_agent": bound_agent}


# ─────────────────── 绑定 Agent + 版本 ───────────────────

def bind_to_agent(agent_id: str, skill_id: str, *, uid: str = "", team: bool = False, knowledge: str = "") -> dict:
    """把 Skill 绑进 Agent。team=True 写 agent.json（团队绑定 + 版本 +1）；否则写用户私有绑定。"""
    if team:
        ajp = paths.agent_json(agent_id)
        agent = read_json(ajp)
        if agent is None:
            raise APIError(404, ErrorCode.NOT_FOUND, f"Agent 不存在: {agent_id}")
        skills = list(agent.get("skills", []))
        if skill_id not in skills:
            skills.append(skill_id)
        know = dict(agent.get("skill_knowledge", {}))
        if knowledge:
            know[skill_id] = knowledge
        agent = {**agent, "skills": skills, "skill_knowledge": know,
                 "version": int(agent.get("version", 1)) + 1, "updated_at": _now_iso()}
        write_json(ajp, agent)
        audit_svc.record(actor="system", action="skill_bind",
                         summary=f"团队绑定 Skill {skill_id} → Agent {agent_id} (v{agent['version']})",
                         detail={"agent_id": agent_id, "skill_id": skill_id, "scope": "team"})
        return {"agent_id": agent_id, "version": agent["version"], "bound": skill_id, "scope": "team"}

    if not uid:
        raise APIError(400, ErrorCode.BAD_REQUEST, "个人绑定需 uid")
    bpath = paths.agent_user_skill_bindings(agent_id, uid)
    bindings = read_json(bpath, default={"skills": []}) or {"skills": []}
    items = list(bindings.get("skills", []))
    if not any(b.get("skill_id") == skill_id for b in items):
        items.append({"skill_id": skill_id, "knowledge": knowledge, "bound_at": _now_iso()})
    write_json(bpath, {"skills": items})
    return {"agent_id": agent_id, "user": uid, "bound": skill_id, "scope": "user"}


def list_agent_bindings(agent_id: str, *, uid: str = "") -> dict:
    """汇总 Agent 的 Skill 绑定：团队（agent.json.skills）+ 当前用户私有绑定。"""
    agent = read_json(paths.agent_json(agent_id)) or {}
    team_skill_ids = [s for s in agent.get("skills", []) if str(s).startswith("sk_")]
    user_items: list[dict] = []
    if uid:
        b = read_json(paths.agent_user_skill_bindings(agent_id, uid), default={"skills": []}) or {"skills": []}
        user_items = b.get("skills", [])
    return {
        "agent_id": agent_id,
        "builtin_skills": [s for s in agent.get("skills", []) if not str(s).startswith("sk_")],
        "team_skills": team_skill_ids,
        "user_skills": user_items,
        "skill_knowledge": agent.get("skill_knowledge", {}),
        "agent_version": agent.get("version", 1),
    }


def bump_agent_version(agent_id: str, *, note: str = "") -> dict:
    ajp = paths.agent_json(agent_id)
    agent = read_json(ajp)
    if agent is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"Agent 不存在: {agent_id}")
    agent = {**agent, "version": int(agent.get("version", 1)) + 1, "updated_at": _now_iso()}
    write_json(ajp, agent)
    return {"agent_id": agent_id, "version": agent["version"], "note": note}


def rollback_skill(skill_id: str, target_version: int, *, uid: str = "") -> dict:
    """回滚 Skill 到历史版本（写新版本，不删历史）。"""
    skill = skill_svc.get_skill(skill_id, uid=uid)
    available = {m["version"] for m in skill_svc.list_versions(skill)}
    if int(target_version) not in available:
        raise APIError(404, ErrorCode.NOT_FOUND, f"版本不存在: v{target_version}")
    old_code = skill_svc.read_skill_code(skill, version=int(target_version))
    new_skill = skill_svc.save_new_version(skill, old_code, note=f"rollback to v{target_version}")
    audit_svc.record(actor=uid or "system", action="skill_rollback",
                     summary=f"Skill {skill_id} 回滚到 v{target_version} → v{new_skill['version']}",
                     detail={"skill_id": skill_id, "target_version": int(target_version)})
    return {"skill_id": skill_id, "version": new_skill["version"], "rolled_back_to": int(target_version)}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
