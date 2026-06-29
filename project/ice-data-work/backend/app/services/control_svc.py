"""执行控制：一键暂停（材料一治理 / 材料二 §8）。

全局暂停开关 + 任务级暂停（任务级走 task_svc 的 paused 状态）。
全局暂停时：agent_runtime 拒绝新回合、ws 拒绝新消息、高风险工具不执行。
控制状态落盘 .cache/control.json（派生/运行态，非 G3 真相源）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.storage.jsonio import read_json, write_json


def _control_path():
    return get_settings().cache_dir / "control.json"


def is_paused() -> bool:
    """全局是否处于暂停状态。"""
    state = read_json(_control_path(), default={})
    return bool(state.get("global_paused", False))


def get_state() -> dict:
    state = read_json(_control_path(), default={})
    return {
        "global_paused": bool(state.get("global_paused", False)),
        "paused_by": state.get("paused_by", ""),
        "paused_at": state.get("paused_at", ""),
    }


def pause_all(actor: str) -> dict:
    """一键暂停全部执行。"""
    state = {
        "global_paused": True,
        "paused_by": actor,
        "paused_at": _now_iso(),
    }
    p = _control_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(p, state)
    return state


def resume_all(actor: str) -> dict:
    """恢复全部执行。"""
    state = {
        "global_paused": False,
        "resumed_by": actor,
        "resumed_at": _now_iso(),
    }
    p = _control_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(p, state)
    return state


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
