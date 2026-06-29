"""Agent 运行时：有界 ReAct + 按 speaker 切换 + 有界多跳 A2A 编排（材料二 §6 / M7-T01）。

run_agent_turn 是生成器，产出标准事件（带 speaker）供 WebSocket/SSE 透传：
    {"type": "turn_start", "speaker": {...}, "handoff": {...}?}
    {"type": "text", "delta": "...", "speaker": {...}}
    {"type": "tool_use", "tool": "...", "args": {...}, "result": {...}, "speaker": {...}}
    {"type": "handoff", "from": {...}, "to": {...}, "reason": "...", "honored": bool, "speaker": {...}}
    {"type": "turn_done", "content": "...", "speaker": {...}}
    {"type": "error", "message": "...", "error_info": {...}, "speaker": {...}}

v1：Twin 编排路由——用户发言默认由 Twin 接管；@定向时强制指定参与者（单跳）。
v1.5（M7，IDW_A2A_ENABLED）：单轮内有界多跳——A 产出 → 解析转交指令 → Twin 仲裁 → B 接力…
    多跳必须有界（max_hops 默认 3，硬顶 6）+ 防环（A↔B/自转交/重复转交）+ 预算。
治理：全局暂停时拒绝新回合；错误结构化分类；LLM 用量落账；审计记录（每跳）。
"""
from __future__ import annotations

from typing import Iterator

from app.core.config import get_settings
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json
from app.services import (
    audit_svc,
    context_assembler_svc,
    control_svc,
    conversation_svc,
    error_classifier,
    llm_gateway,
    orchestrator_svc,
    task_svc,
    usage_svc,
)
from app.services.tools import run_tool

MAX_ROUNDS = 20
HARD_CAP = 50


def resolve_speaker(task: dict, *, mentioned: str | None = None) -> dict:
    """决定本轮执行主体。

    优先级：@定向 > 任务 assignee > 第一个 twin 参与者 > 第一个 agent 参与者。
    """
    participants = task.get("participants", [])

    if mentioned:
        for p in participants:
            if p.get("ref_id") == mentioned:
                return {"type": p["ref_type"], "id": p["ref_id"]}

    assignee = task.get("assignee")
    if assignee and assignee.get("type") in ("twin", "agent"):
        return {"type": assignee["type"], "id": assignee["id"]}

    # Twin 编排优先
    for p in participants:
        if p.get("ref_type") == "twin":
            return {"type": "twin", "id": p["ref_id"]}
    for p in participants:
        if p.get("ref_type") == "agent":
            return {"type": "agent", "id": p["ref_id"]}

    # 兜底：assistant
    return {"type": "agent", "id": "general"}


def _agent_ids(task: dict) -> tuple[set[str], set[str]]:
    """返回 (参与本任务的 agent id 集合, 平台已知 agent id 集合)。"""
    participant_agent_ids = {
        p["ref_id"] for p in task.get("participants", []) if p.get("ref_type") == "agent"
    }
    known: set[str] = set()
    for d in iter_dirs(paths.root() / "agents"):
        meta = read_json(d / "agent.json")
        if meta and meta.get("id"):
            known.add(meta["id"])
    return participant_agent_ids, known


def run_agent_turn(
    task_id: str,
    *,
    user_message: str,
    acting_user_id: str,
    mentioned: str | None = None,
    model: str = "claude-sonnet-4",
) -> Iterator[dict]:
    """执行一个对话回合。开关 IDW_A2A_ENABLED 决定是否单轮内多跳接力。"""
    # 治理：全局暂停拦截
    if control_svc.is_paused():
        yield {"type": "error", "message": "系统已被一键暂停，暂不执行新回合",
               "error_info": {"error_type": "paused", "recoverable": True,
                              "suggested": "在治理页恢复执行后重试"},
               "speaker": {"type": "agent", "id": "system"}}
        return

    task = task_svc.get_task(task_id)

    # 1) 落盘用户发言
    if user_message:
        conversation_svc.append_turn(
            task_id, speaker_type="user", speaker_id=acting_user_id, content=user_message,
        )

    # 2) 任务进入执行中
    if task.get("status") in ("todo", "await", "error", "paused"):
        try:
            task_svc.set_status(task_id, "doing")
            task = task_svc.get_task(task_id)
        except Exception:
            pass

    # 3) 决定初始 speaker
    speaker = resolve_speaker(task, mentioned=mentioned)

    a2a_enabled = get_settings().a2a_enabled
    state = orchestrator_svc.new_hop_state(speaker)
    incoming_handoff: dict | None = None

    while True:
        hop = yield from _run_single_hop(
            task_id, speaker=speaker, acting_user_id=acting_user_id,
            model=model, handoff=incoming_handoff,
        )

        # 单跳模式（开关关）或本跳出错 → 结束
        if not a2a_enabled or hop["errored"]:
            break

        # 解析转交指令
        req = orchestrator_svc.parse_directive(hop["raw"])
        if not req:
            break

        # 刷新任务（参与者可能在上一跳变化）并仲裁
        task = task_svc.get_task(task_id)
        participant_ids, known_ids = _agent_ids(task)
        decision = orchestrator_svc.arbitrate_handoff(
            request=req, current_speaker=speaker, state=state,
            participant_agent_ids=participant_ids, known_agent_ids=known_ids,
        )

        target = decision["target"] or {"type": "agent", "id": req.get("to", "")}
        yield {
            "type": "handoff",
            "from": speaker,
            "to": target,
            "reason": req.get("reason", ""),
            "action": req.get("action", orchestrator_svc.ACTION_HANDOFF),
            "honored": decision["honor"],
            "note": "" if decision["honor"] else decision["reason"],
            "speaker": speaker,
        }

        if not decision["honor"]:
            break

        # 目标未参与则自动以 tool 角色加入（不放宽其权限）
        if decision["auto_join"]:
            try:
                task_svc.add_participant(task_id, "agent", target["id"],
                                         role="tool", permission_level="L2")
            except Exception:
                pass

        orchestrator_svc.record_hop(state, from_speaker=speaker, target=target)
        incoming_handoff = {"from": speaker["id"], "to": target["id"], "reason": req.get("reason", "")}
        speaker = target


def _run_single_hop(
    task_id: str,
    *,
    speaker: dict,
    acting_user_id: str,
    model: str,
    handoff: dict | None = None,
) -> Iterator[dict]:
    """执行单个 speaker 的一跳：组装上下文 → 流式 LLM → 落盘 + 审计 + 用量。

    生成器返回 {"raw": 原始文本, "content": 清洗后文本, "errored": bool}（供编排器解析转交）。
    """
    task = task_svc.get_task(task_id)
    start_evt: dict = {"type": "turn_start", "speaker": speaker}
    if handoff:
        start_evt["handoff"] = handoff
    yield start_evt

    # 组装上下文（被转交方注入前序产出摘要 + 转交理由，见 context_assembler A2A 层）
    messages_meta = context_assembler_svc.assemble_context(
        task, speaker=speaker, acting_user_id=acting_user_id, handoff=handoff,
    )
    messages = context_assembler_svc.strip_meta(messages_meta)

    full_text: list[str] = []
    errored = False
    try:
        for evt in llm_gateway.stream_chat(messages, model=model):
            if evt["type"] == "text":
                full_text.append(evt["delta"])
                yield {"type": "text", "delta": evt["delta"], "speaker": speaker}
            elif evt["type"] == "error":
                errored = True
                info = error_classifier.classify(evt.get("message", ""))
                yield {"type": "error", "message": evt["message"], "error_info": info, "speaker": speaker}
            elif evt["type"] == "done":
                if evt.get("content") and not full_text:
                    full_text.append(evt["content"])
                _record_usage(evt, task_id, acting_user_id, model)
    except Exception as e:
        errored = True
        info = error_classifier.classify(str(e))
        yield {"type": "error", "message": f"运行时错误: {e}", "error_info": info, "speaker": speaker}

    raw = "".join(full_text)
    content = orchestrator_svc.strip_directives(raw)

    # 落盘 speaker 回合（清洗后文本）+ 审计
    conversation_svc.append_turn(
        task_id, speaker_type=speaker["type"], speaker_id=speaker["id"],
        content=content, handoff=handoff,
    )
    audit_svc.record(
        actor=acting_user_id, action="agent_turn", task_id=task_id,
        result="error" if errored else "ok",
        summary=f"{speaker['type']}:{speaker['id']} 回应（{len(content)} 字）"
                + (f"（接力自 {handoff['from']}）" if handoff else ""),
    )

    if errored:
        try:
            task_svc.set_status(task_id, "error", reason="LLM/运行时错误")
        except Exception:
            pass

    yield {"type": "turn_done", "content": content, "speaker": speaker}
    return {"raw": raw, "content": content, "errored": errored}


def execute_tool(
    task_id: str, tool_name: str, args: dict, *, speaker_id: str, approved: bool = False,
) -> dict:
    """显式工具执行入口（HITL 确认后调用）。记录到 tool_calls.jsonl + 审计。"""
    if control_svc.is_paused():
        return {"ok": False, "error_code": "PAUSED", "message": "系统已被一键暂停", "data": None}

    ctx = {"task_id": task_id, "speaker_id": speaker_id, "approved": approved}
    result = run_tool(tool_name, args, context=ctx)
    conversation_svc.append_tool_call(
        task_id, tool=tool_name, args=args, result=result,
        speaker_id=speaker_id, status="ok" if result.get("ok") else "error",
    )
    audit_svc.record(
        actor=speaker_id, action="tool_call", task_id=task_id, tool=tool_name,
        result="ok" if result.get("ok") else "error",
        summary=result.get("message", ""),
    )
    return result


def _record_usage(done_evt: dict, task_id: str, user_id: str, model: str) -> None:
    """从 done 事件落 LLM 用量。"""
    usage = done_evt.get("usage", {})
    is_mock = bool(usage.get("mock"))
    try:
        usage_svc.record_usage(
            model=model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", len(done_evt.get("content", "")) // 4),
            task_id=task_id, user_id=user_id, mock=is_mock,
        )
    except Exception:
        pass
