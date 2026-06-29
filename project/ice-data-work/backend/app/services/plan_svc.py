"""任务计划服务：plan.json 步骤编排（M7-T06 / D-17）。

任务级 6 态（task_svc）与步骤级状态正交：plan 描述"怎么一步步做"，是编排真相源。
plan.json 走 G3 文件 + file_transaction（原子写 + 锁 + 回滚）。

数据结构 tasks/{tid}/plan.json：
    {
      "task_id": "...",
      "goal": "...",                       # 任务目标（M7-T08）
      "definition_of_done": "...",         # 完成判据（M7-T08）
      "steps": [
        {"id":"step_xxx","title":"...","owner_agent":"data-analysis",
         "status":"todo|doing|done|error|skipped","result_ref":"","depends_on":[],
         "created_at":...,"updated_at":...}
      ],
      "current_step": "step_xxx"|None,
      "created_at":..., "updated_at":...
    }
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import read_json, write_json
from app.core.storage.transaction import file_transaction

STEP_TODO = "todo"
STEP_DOING = "doing"
STEP_DONE = "done"
STEP_ERROR = "error"
STEP_SKIPPED = "skipped"
STEP_STATUSES = {STEP_TODO, STEP_DOING, STEP_DONE, STEP_ERROR, STEP_SKIPPED}


# ─── 读取 ───

def get_plan(task_id: str) -> dict | None:
    return read_json(paths.task_plan(task_id))


def get_plan_or_empty(task_id: str) -> dict:
    """读取计划；不存在返回空壳（不落盘）。"""
    return get_plan(task_id) or {
        "task_id": task_id, "goal": "", "definition_of_done": "",
        "steps": [], "current_step": None,
    }


# ─── 写入（均走 file_transaction）───

def ensure_plan(task_id: str, *, goal: str = "", definition_of_done: str = "") -> dict:
    """确保计划存在；已存在则按需更新 goal/DoD。"""
    with file_transaction([paths.task_plan(task_id)]):
        plan = get_plan(task_id)
        if plan is None:
            plan = {
                "task_id": task_id, "goal": goal, "definition_of_done": definition_of_done,
                "steps": [], "current_step": None,
                "created_at": _now_iso(), "updated_at": _now_iso(),
            }
        else:
            if goal:
                plan["goal"] = goal
            if definition_of_done:
                plan["definition_of_done"] = definition_of_done
            plan["updated_at"] = _now_iso()
        paths.ensure(paths.task_plan(task_id))
        write_json(paths.task_plan(task_id), plan)
    return plan


def set_goal(task_id: str, *, goal: str | None = None, definition_of_done: str | None = None) -> dict:
    with file_transaction([paths.task_plan(task_id)]):
        plan = _load(task_id)
        if goal is not None:
            plan["goal"] = goal
        if definition_of_done is not None:
            plan["definition_of_done"] = definition_of_done
        plan["updated_at"] = _now_iso()
        write_json(paths.task_plan(task_id), plan)
    return plan


def replace_steps(task_id: str, steps: list[dict]) -> dict:
    """整体替换步骤（Twin 据 goal 拆解后写入）。保留/重置 current_step 到第一个就绪步。"""
    norm: list[dict] = []
    for s in steps:
        norm.append(_new_step(
            title=s.get("title", ""), owner_agent=s.get("owner_agent", ""),
            depends_on=s.get("depends_on", []), status=s.get("status", STEP_TODO),
        ))
    with file_transaction([paths.task_plan(task_id)]):
        plan = get_plan(task_id) or _blank(task_id)
        plan["steps"] = norm
        plan["current_step"] = None
        plan["updated_at"] = _now_iso()
        paths.ensure(paths.task_plan(task_id))
        write_json(paths.task_plan(task_id), plan)
    return plan


def add_step(task_id: str, *, title: str, owner_agent: str = "",
             depends_on: list[str] | None = None) -> dict:
    if not title.strip():
        raise APIError(400, ErrorCode.BAD_REQUEST, "步骤标题不能为空")
    step = _new_step(title=title, owner_agent=owner_agent, depends_on=depends_on or [])
    with file_transaction([paths.task_plan(task_id)]):
        plan = get_plan(task_id) or _blank(task_id)
        plan["steps"].append(step)
        plan["updated_at"] = _now_iso()
        paths.ensure(paths.task_plan(task_id))
        write_json(paths.task_plan(task_id), plan)
    return step


def update_step(task_id: str, step_id: str, *, status: str | None = None,
                result_ref: str | None = None, title: str | None = None,
                owner_agent: str | None = None) -> dict:
    if status is not None and status not in STEP_STATUSES:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"非法步骤状态: {status}")
    with file_transaction([paths.task_plan(task_id)]):
        plan = _load(task_id)
        step = _find_step(plan, step_id)
        if status is not None:
            step["status"] = status
        if result_ref is not None:
            step["result_ref"] = result_ref
        if title is not None:
            step["title"] = title
        if owner_agent is not None:
            step["owner_agent"] = owner_agent
        step["updated_at"] = _now_iso()
        # current_step 维护：done/skipped 则推进到下一就绪步
        if status in (STEP_DONE, STEP_SKIPPED):
            nxt = _next_ready(plan)
            plan["current_step"] = nxt["id"] if nxt else None
        elif status == STEP_DOING:
            plan["current_step"] = step_id
        plan["updated_at"] = _now_iso()
        write_json(paths.task_plan(task_id), plan)
    return step


def start_next(task_id: str) -> dict | None:
    """把下一个就绪步置 doing 并设为 current_step；无就绪步返回 None。"""
    with file_transaction([paths.task_plan(task_id)]):
        plan = _load(task_id)
        nxt = _next_ready(plan)
        if nxt is None:
            return None
        nxt["status"] = STEP_DOING
        nxt["updated_at"] = _now_iso()
        plan["current_step"] = nxt["id"]
        plan["updated_at"] = _now_iso()
        write_json(paths.task_plan(task_id), plan)
    return nxt


# ─── 查询/计算 ───

def next_ready_step(task_id: str) -> dict | None:
    plan = get_plan(task_id)
    return _next_ready(plan) if plan else None


def current_step(task_id: str) -> dict | None:
    plan = get_plan(task_id)
    if not plan or not plan.get("current_step"):
        return None
    return next((s for s in plan["steps"] if s["id"] == plan["current_step"]), None)


def progress(task_id: str) -> dict:
    """步骤进度：{total, done, current_index, current_title}。供卡片副行"现在：X（n/m）"。"""
    plan = get_plan(task_id)
    if not plan or not plan.get("steps"):
        return {"total": 0, "done": 0, "current_index": 0, "current_title": ""}
    steps = plan["steps"]
    done = sum(1 for s in steps if s["status"] in (STEP_DONE, STEP_SKIPPED))
    cur = current_step(task_id)
    cur_idx = next((i for i, s in enumerate(steps) if cur and s["id"] == cur["id"]), done)
    return {
        "total": len(steps), "done": done,
        "current_index": cur_idx + 1 if cur else done,
        "current_title": cur["title"] if cur else "",
    }


def is_plan_complete(task_id: str) -> bool:
    """全部步骤 done/skipped（无步骤视为未完成，避免空计划误判）。"""
    plan = get_plan(task_id)
    if not plan or not plan.get("steps"):
        return False
    return all(s["status"] in (STEP_DONE, STEP_SKIPPED) for s in plan["steps"])


# ─── 内部 ───

def _blank(task_id: str) -> dict:
    return {
        "task_id": task_id, "goal": "", "definition_of_done": "",
        "steps": [], "current_step": None,
        "created_at": _now_iso(), "updated_at": _now_iso(),
    }


def _load(task_id: str) -> dict:
    plan = get_plan(task_id)
    if plan is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"任务计划不存在: {task_id}")
    return plan


def _find_step(plan: dict, step_id: str) -> dict:
    step = next((s for s in plan.get("steps", []) if s["id"] == step_id), None)
    if step is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"步骤不存在: {step_id}")
    return step


def _next_ready(plan: dict) -> dict | None:
    """第一个 todo 且依赖全部 done/skipped 的步骤。"""
    done_ids = {s["id"] for s in plan.get("steps", []) if s["status"] in (STEP_DONE, STEP_SKIPPED)}
    for s in plan.get("steps", []):
        if s["status"] != STEP_TODO:
            continue
        if all(dep in done_ids for dep in s.get("depends_on", [])):
            return s
    return None


def _new_step(*, title: str, owner_agent: str, depends_on: list[str], status: str = STEP_TODO) -> dict:
    return {
        "id": f"step_{uuid.uuid4().hex[:8]}",
        "title": title.strip(),
        "owner_agent": owner_agent,
        "status": status if status in STEP_STATUSES else STEP_TODO,
        "result_ref": "",
        "depends_on": list(depends_on or []),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────── M7-T07：计划编排（拆解 + 推进）───────────────────

import re as _re  # noqa: E402

_CLAUSE_SPLIT = _re.compile(r"[\n；;。]+|(?:^|\s)\d+[.)、]\s*")


def decompose_goal(goal: str, agent_ids: list[str] | None = None, *, max_steps: int = 6) -> list[dict]:
    """把目标拆成有序步骤（确定性，mock LLM 也可用）。

    拆分线索：换行 / 中英分号 / 句号 / 编号列表（1. 2) 3、）。
    owner_agent 在可用 agent 间轮转；无 agent 则留空（由 Twin 兜底）。
    顺序即依赖：执行时按列表序逐个就绪（无需显式 depends_on）。
    """
    agents = list(agent_ids or [])
    clauses = [c.strip() for c in _CLAUSE_SPLIT.split(goal or "") if c and c.strip()]
    if not clauses:
        clauses = [f"完成：{(goal or '').strip()}"] if (goal or "").strip() else []
    steps: list[dict] = []
    for i, c in enumerate(clauses[:max_steps]):
        owner = agents[i % len(agents)] if agents else ""
        steps.append({"title": c, "owner_agent": owner})
    return steps


def plan_advance_after_turn(task_id: str, *, errored: bool = False, error_message: str = "") -> dict:
    """一轮结束后推进计划：成功则当前步 done + 起下一步；失败则当前步 error + 给建议。

    返回 {current, next, failed, suggestion}。无计划/无步骤时全 None。
    """
    plan = get_plan(task_id)
    result: dict = {"current": None, "next": None, "failed": None, "suggestion": None}
    if not plan or not plan.get("steps"):
        return result

    cur = current_step(task_id)
    result["current"] = cur
    if cur is None:
        result["next"] = start_next(task_id)
        return result

    if errored:
        from app.services import error_classifier
        update_step(task_id, cur["id"], status=STEP_ERROR)
        result["failed"] = cur
        result["suggestion"] = error_classifier.classify(error_message or "")
    else:
        update_step(task_id, cur["id"], status=STEP_DONE)
        result["next"] = start_next(task_id)
    return result


def step_owner(task_id: str) -> str:
    """当前步的 owner_agent（供编排器把发言权路由给负责该步的 Agent）。"""
    cur = current_step(task_id)
    return (cur or {}).get("owner_agent", "") if cur else ""
