"""Skill 自演进路由（D-13）：候选 / 个人草稿 / 沙盒 test-run / 团队晋升（双门）/ 绑定 / 回滚。

晋升双门：
    门1 沙盒 test-run 通过 —— 由 skill_evolve_svc.promote_to_team 内部校验 test_passed。
    门2 owner/admin 审核   —— 由 require_member("tid", ADMIN) 把关（平台 admin 自动放行）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user, require_member
from app.core.errors import ok
from app.core.permissions import MemberRole
from app.services import hitl_svc, skill_evolve_svc, skill_svc, task_svc

router = APIRouter(prefix="/skills", tags=["skills"])


# ─────────────────── 候选 ───────────────────

@router.get("/candidates")
def list_candidates(task_id: str, status: str | None = None, user: dict = Depends(get_current_user)) -> dict:
    """列出任务的 Skill 候选（run_user_code 跑通后由 propose_skill 生成）。"""
    task_svc.get_task(task_id)
    return ok(skill_svc.list_skill_candidates(task_id, status=status))


class MaterializeReq(BaseModel):
    task_id: str
    candidate_id: str
    bind: bool = True


@router.post("/materialize")
def materialize(body: MaterializeReq, user: dict = Depends(get_current_user)) -> dict:
    """表单确认 → 落个人草稿（立即可用）+ 绑定 Agent；by_team 额外发审批。"""
    task_svc.get_task(body.task_id)
    return ok(
        skill_evolve_svc.materialize_candidate(
            body.task_id, body.candidate_id, decided_by=user["id"], uid=user["id"], bind=body.bind,
        ),
        message="已沉淀为个人草稿 Skill",
    )


# ─────────────────── 列表 / 详情 ───────────────────

@router.get("/mine")
def my_skills(user: dict = Depends(get_current_user)) -> dict:
    """当前用户的草稿 Skill。"""
    return ok(skill_svc.list_user_skills(user["id"]))


@router.get("/team")
def team_skills(tid: str = "", user: dict = Depends(get_current_user)) -> dict:
    """团队共享 Skill（可按 tid 过滤）。"""
    return ok(skill_svc.list_team_skills(tid))


@router.get("/agent/{agent_id}")
def agent_bindings(agent_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Agent 的 Skill 绑定汇总（内置 + 团队 + 当前用户私有 + knowledge）。"""
    return ok(skill_evolve_svc.list_agent_bindings(agent_id, uid=user["id"]))


# ─────────────────── 沙盒 test-run ───────────────────

class TestRunReq(BaseModel):
    skill_id: str
    sample_params: dict | None = None


@router.post("/test-run")
def test_run(body: TestRunReq, user: dict = Depends(get_current_user)) -> dict:
    """对 Skill 当前版本做一次沙盒 test-run（团队晋升前置门1）。"""
    return ok(skill_svc.test_run(body.skill_id, uid=user["id"], sample_params=body.sample_params))


# ─────────────────── 团队晋升（双门）───────────────────

class PromoteReq(BaseModel):
    skill_id: str
    agent_id: str = ""
    task_id: str = ""
    approval_id: str = ""


@router.post("/promote/{tid}")
def promote(tid: str, body: PromoteReq,
            user: dict = Depends(require_member("tid", MemberRole.ADMIN))) -> dict:
    """个人草稿 → 团队 Skill。门2（owner/admin）由 require_member 把关；门1（test-run）在服务层。"""
    result = skill_evolve_svc.promote_to_team(
        body.skill_id, uid=user["id"], tid=tid, decided_by=user["id"], agent_id=body.agent_id,
    )
    if body.task_id and body.approval_id:
        try:
            hitl_svc.decide(body.task_id, body.approval_id, approved=True,
                            decided_by=user["id"], reason="团队晋升通过（test-run + owner/admin 双门）")
        except Exception:
            pass
    return ok(result, message="已晋升为团队 Skill")


# ─────────────────── 绑定 / 回滚 ───────────────────

class BindReq(BaseModel):
    agent_id: str
    skill_id: str
    knowledge: str = ""


@router.post("/bind")
def bind(body: BindReq, user: dict = Depends(get_current_user)) -> dict:
    """把 Skill 绑进 Agent（个人私有绑定，仅当前用户生效）。"""
    return ok(skill_evolve_svc.bind_to_agent(
        body.agent_id, body.skill_id, uid=user["id"], team=False, knowledge=body.knowledge,
    ))


class RollbackReq(BaseModel):
    skill_id: str
    version: int


@router.post("/rollback")
def rollback(body: RollbackReq, user: dict = Depends(get_current_user)) -> dict:
    """回滚 Skill 到历史版本（写新版本，不删历史）。"""
    return ok(skill_evolve_svc.rollback_skill(body.skill_id, body.version, uid=user["id"]))


# 单段路径参数放最后，避免吞掉 /mine /team /candidates 等静态路径
@router.get("/{skill_id}")
def get_skill(skill_id: str, user: dict = Depends(get_current_user)) -> dict:
    skill = skill_svc.get_skill(skill_id, uid=user["id"])
    return ok({**skill, "versions": skill_svc.list_versions(skill)})
