"""任务路由：CRUD + 状态流转 + 参与者 + 会话 + 计划/步骤（需认证）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.errors import ok
from app.services import conversation_svc, plan_svc, task_svc

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskReq(BaseModel):
    title: str
    project_id: str | None = None
    type: str = "general"
    participants: list[dict] | None = None
    assignee: dict | None = None
    goal: str = ""
    definition_of_done: str = ""


class UpdateTaskReq(BaseModel):
    title: str | None = None
    assignee: dict | None = None
    goal: str | None = None
    definition_of_done: str | None = None


class StatusReq(BaseModel):
    status: str
    reason: str = ""
    confirm: bool = False  # DoD 门控：用户显式确认完成（M7-T08）


class ParticipantReq(BaseModel):
    ref_type: str
    ref_id: str
    role: str = "collaborator"
    permission_level: str = "L2"


class TurnReq(BaseModel):
    content: str
    speaker_type: str = "user"
    speaker_id: str = ""


class PlanGoalReq(BaseModel):
    goal: str | None = None
    definition_of_done: str | None = None


class DecomposeReq(BaseModel):
    goal: str | None = None  # 缺省用任务 goal


class StepReq(BaseModel):
    title: str
    owner_agent: str = ""
    depends_on: list[str] | None = None


class StepUpdateReq(BaseModel):
    status: str | None = None
    result_ref: str | None = None
    title: str | None = None
    owner_agent: str | None = None


# ─── 任务 CRUD ───

@router.get("")
def list_tasks(
    project_id: str | None = None,
    status: str | None = None,
    mine: bool = False,
    user: dict = Depends(get_current_user),
) -> dict:
    """列出任务。mine=true 只看自己参与的。"""
    tasks = task_svc.list_tasks(
        project_id=project_id,
        status=status,
        user_id=user["id"] if mine else None,
    )
    return ok(tasks)


@router.post("")
def create_task(body: CreateTaskReq, user: dict = Depends(get_current_user)) -> dict:
    """创建任务。缺省 project_id 落用户个人项目（D-11）。"""
    project_id = body.project_id or f"p_personal_{user['id']}"
    result = task_svc.create_task(
        title=body.title,
        project_id=project_id,
        created_by=user["id"],
        task_type=body.type,
        participants=body.participants,
        assignee=body.assignee,
        goal=body.goal,
        definition_of_done=body.definition_of_done,
    )
    return ok(result)


@router.get("/{task_id}")
def get_task(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(task_svc.get_task(task_id))


@router.put("/{task_id}")
def update_task(task_id: str, body: UpdateTaskReq, user: dict = Depends(get_current_user)) -> dict:
    return ok(task_svc.update_task(
        task_id, title=body.title, assignee=body.assignee,
        goal=body.goal, definition_of_done=body.definition_of_done,
    ))


@router.put("/{task_id}/status")
def set_status(task_id: str, body: StatusReq, user: dict = Depends(get_current_user)) -> dict:
    return ok(task_svc.set_status(task_id, body.status, reason=body.reason, confirm=body.confirm))


@router.delete("/{task_id}")
def delete_task(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    task_svc.delete_task(task_id)
    return ok(None, message="已删除")


# ─── 参与者 ───

@router.get("/{task_id}/participants")
def list_participants(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    return ok(task_svc.list_participants(task_id))


@router.post("/{task_id}/participants")
def add_participant(task_id: str, body: ParticipantReq, user: dict = Depends(get_current_user)) -> dict:
    result = task_svc.add_participant(
        task_id, body.ref_type, body.ref_id,
        role=body.role, permission_level=body.permission_level,
    )
    return ok(result)


@router.delete("/{task_id}/participants/{ref_type}/{ref_id}")
def remove_participant(
    task_id: str, ref_type: str, ref_id: str, user: dict = Depends(get_current_user),
) -> dict:
    return ok(task_svc.remove_participant(task_id, ref_type, ref_id))


# ─── 会话 ───

@router.get("/{task_id}/conversation")
def get_conversation(task_id: str, limit: int | None = None, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(task_id)  # 校验存在
    return ok(conversation_svc.get_conversation(task_id, limit=limit))


@router.post("/{task_id}/turns")
def append_turn(task_id: str, body: TurnReq, user: dict = Depends(get_current_user)) -> dict:
    """追加用户回合（非流式；流式走 WebSocket）。"""
    task_svc.get_task(task_id)  # 校验存在
    speaker_id = body.speaker_id or user["id"]
    turn = conversation_svc.append_turn(
        task_id,
        speaker_type=body.speaker_type,
        speaker_id=speaker_id,
        content=body.content,
    )
    return ok(turn)


@router.get("/{task_id}/tool-calls")
def get_tool_calls(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(task_id)
    return ok(conversation_svc.get_tool_calls(task_id))


# ─── 计划 / 步骤（M7-T06/T07/T09）───

@router.get("/{task_id}/plan")
def get_plan(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    """读取任务计划 + 进度（供卡片副行"现在：X（n/m）"）。"""
    task_svc.get_task(task_id)
    return ok({"plan": plan_svc.get_plan_or_empty(task_id), "progress": plan_svc.progress(task_id)})


@router.put("/{task_id}/plan")
def set_plan_goal(task_id: str, body: PlanGoalReq, user: dict = Depends(get_current_user)) -> dict:
    """设置目标 + 完成判据（同步到 task.json 供 DoD 门控，并镜像到计划）。"""
    task_svc.update_task(task_id, goal=body.goal, definition_of_done=body.definition_of_done)
    plan = plan_svc.ensure_plan(task_id, goal=body.goal or "", definition_of_done=body.definition_of_done or "")
    return ok(plan)


@router.post("/{task_id}/plan/decompose")
def decompose_plan(task_id: str, body: DecomposeReq, user: dict = Depends(get_current_user)) -> dict:
    """据目标自动拆解步骤并指派可用 Agent（Twin 计划编排，M7-T07）。"""
    task = task_svc.get_task(task_id)
    goal = (body.goal or task.get("goal") or "").strip()
    agent_ids = [p["ref_id"] for p in task.get("participants", []) if p.get("ref_type") == "agent"]
    steps = plan_svc.decompose_goal(goal, agent_ids)
    plan_svc.ensure_plan(task_id, goal=goal, definition_of_done=task.get("definition_of_done", ""))
    plan = plan_svc.replace_steps(task_id, steps)
    return ok({"plan": plan, "progress": plan_svc.progress(task_id)})


@router.post("/{task_id}/plan/steps")
def add_step(task_id: str, body: StepReq, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(task_id)
    plan_svc.ensure_plan(task_id)
    step = plan_svc.add_step(task_id, title=body.title, owner_agent=body.owner_agent,
                             depends_on=body.depends_on)
    return ok(step)


@router.put("/{task_id}/steps/{step_id}")
def update_step(task_id: str, step_id: str, body: StepUpdateReq,
                user: dict = Depends(get_current_user)) -> dict:
    return ok(plan_svc.update_step(
        task_id, step_id, status=body.status, result_ref=body.result_ref,
        title=body.title, owner_agent=body.owner_agent,
    ))


@router.post("/{task_id}/plan/start-next")
def start_next_step(task_id: str, user: dict = Depends(get_current_user)) -> dict:
    task_svc.get_task(task_id)
    return ok(plan_svc.start_next(task_id))
