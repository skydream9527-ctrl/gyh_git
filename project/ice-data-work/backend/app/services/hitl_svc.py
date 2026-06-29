"""HITL 服务：人工确认审批队列（材料二 §8）。

审批项落盘 tasks/{tid}/approvals.jsonl（追加型，状态后写覆盖）。
覆盖三类高风险：
    - 工具调用确认（write_file / paid_call / run_command …）
    - 记忆候选晋升到共享空间（agent_team / project / team）
    - 跨空间读取确认（cross_space_read）
审批通过后由调用方执行真实动作（如 memory_svc.promote / tool_runner approved=True）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.storage import paths
from app.core.storage.jsonio import append_jsonl, read_jsonl

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"


def create_approval(
    task_id: str, *, action_type: str, summary: str,
    risk_level: str = RISK_MEDIUM, requester: str = "",
    payload: dict | None = None,
) -> dict:
    """创建审批项。"""
    appr = {
        "id": f"appr_{uuid.uuid4().hex[:8]}",
        "ts": _now_iso(),
        "task_id": task_id,
        "action_type": action_type,
        "summary": summary,
        "risk_level": risk_level,
        "requester": requester,
        "payload": payload or {},
        "status": STATUS_PENDING,
    }
    append_jsonl(paths.task_approvals(task_id), appr)
    return appr


def list_approvals(task_id: str, *, status: str | None = None) -> list[dict]:
    """读取任务审批队列，合并同 id 的状态更新。"""
    records = read_jsonl(paths.task_approvals(task_id))
    latest: dict[str, dict] = {}
    for r in records:
        aid = r.get("id")
        if aid in latest and r.get("_status_update"):
            latest[aid] = {**latest[aid], **{k: v for k, v in r.items() if k != "_status_update"}}
        else:
            latest[aid] = r
    out = list(latest.values())
    if status:
        out = [a for a in out if a.get("status") == status]
    out.sort(key=lambda a: a.get("ts", ""), reverse=True)
    return out


def get_approval(task_id: str, approval_id: str) -> dict:
    appr = next((a for a in list_approvals(task_id) if a["id"] == approval_id), None)
    if appr is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"审批项不存在: {approval_id}")
    return appr


def decide(task_id: str, approval_id: str, *, approved: bool, decided_by: str, reason: str = "") -> dict:
    """裁决审批项。"""
    appr = get_approval(task_id, approval_id)
    if appr["status"] != STATUS_PENDING:
        raise APIError(409, ErrorCode.CONFLICT, f"审批已裁决: {appr['status']}")
    new_status = STATUS_APPROVED if approved else STATUS_REJECTED
    append_jsonl(paths.task_approvals(task_id), {
        "id": approval_id, "status": new_status, "decided_by": decided_by,
        "reason": reason, "decided_at": _now_iso(), "_status_update": True,
    })
    return {**appr, "status": new_status, "decided_by": decided_by}


def list_pending_for_user(user_id: str) -> list[dict]:
    """聚合该用户参与任务的全部待确认项（用于 Workbench / Approvals 页）。"""
    from app.core.storage.jsonio import iter_dirs, read_json
    out: list[dict] = []
    for d in iter_dirs(paths.root() / "tasks"):
        meta = read_json(d / "task.json")
        if meta is None or meta.get("deleted_at"):
            continue
        # 仅用户参与的任务
        if not any(p.get("ref_type") == "user" and p.get("ref_id") == user_id
                   for p in meta.get("participants", [])):
            continue
        pending = list_approvals(meta["id"], status=STATUS_PENDING)
        for a in pending:
            out.append({**a, "task_title": meta.get("title")})
    out.sort(key=lambda a: a.get("ts", ""), reverse=True)
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
