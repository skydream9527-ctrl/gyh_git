"""记忆路由：候选列表 / 晋升(带 scope) / 拒绝 + 审批队列。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.errors import ok
from app.services import hitl_svc, memory_svc, task_svc

router = APIRouter(prefix="/memory", tags=["memory"])


class PromoteReq(BaseModel):
    task_id: str
    candidate_id: str
    scope: str | None = None  # 覆盖候选的 proposed_scope
    # 目标定位（按 scope 需要）
    uid: str = ""
    aid: str = ""
    tid: str = ""
    pid: str = ""


class RejectReq(BaseModel):
    task_id: str
    candidate_id: str
    reason: str = ""


@router.get("/candidates")
def list_candidates(task_id: str, status: str | None = None, user: dict = Depends(get_current_user)) -> dict:
    """列出任务的记忆候选。"""
    task_svc.get_task(task_id)  # 校验存在
    return ok(memory_svc.list_candidates(task_id, status=status))


@router.post("/promote")
def promote(body: PromoteReq, user: dict = Depends(get_current_user)) -> dict:
    """晋升记忆候选到目标空间。

    user_preference 缺省 uid 用当前用户；agent_* 缺省 tid 用任务所属团队。
    """
    task = task_svc.get_task(body.task_id)
    uid = body.uid or user["id"]
    tid = body.tid or _team_of(task)
    result = memory_svc.promote(
        body.task_id, body.candidate_id,
        decided_by=user["id"],
        uid=uid, aid=body.aid, tid=tid, pid=body.pid or task.get("project_id", ""),
        override_scope=body.scope,
    )
    return ok(result, message="已晋升")


@router.post("/reject")
def reject(body: RejectReq, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(body.task_id)
    return ok(memory_svc.reject(body.task_id, body.candidate_id, decided_by=user["id"], reason=body.reason))


def _team_of(task: dict) -> str:
    """从任务 project_id 反查团队 id。"""
    from app.core.storage import paths
    from app.core.storage.jsonio import iter_dirs
    pid = task.get("project_id", "")
    if not pid:
        return ""
    for tdir in iter_dirs(paths.root() / "teams"):
        if (tdir / "projects" / pid / "project.json").exists():
            return tdir.name
    return ""


# ─── 审批队列（HITL）───

approvals_router = APIRouter(prefix="/approvals", tags=["approvals"])


class DecideReq(BaseModel):
    task_id: str
    approval_id: str
    approved: bool
    reason: str = ""


@approvals_router.get("")
def list_my_approvals(user: dict = Depends(get_current_user)) -> dict:
    """聚合当前用户参与任务的全部待确认项。"""
    return ok(hitl_svc.list_pending_for_user(user["id"]))


@approvals_router.get("/{task_id}")
def list_task_approvals(task_id: str, status: str | None = None, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(task_id)
    return ok(hitl_svc.list_approvals(task_id, status=status))


@approvals_router.post("/decide")
def decide(body: DecideReq, user: dict = Depends(get_current_user)) -> dict:
    return ok(hitl_svc.decide(
        body.task_id, body.approval_id, approved=body.approved, decided_by=user["id"], reason=body.reason,
    ))
