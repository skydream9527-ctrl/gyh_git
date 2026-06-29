"""编排器：有界多跳 A2A 的纯逻辑（M7-T01 / D-15）。

本模块只放**纯函数 + 状态机**，不 import agent_runtime（避免循环依赖），便于单测：
    - parse_directive(text)        从 speaker 输出解析转交/咨询指令
    - strip_directives(text)       清除指令标记用于展示/落盘
    - arbitrate_handoff(...)       Twin 作 leader 的转交仲裁（防环 + 预算 + 目标校验）
    - HopState / new_hop_state()   单轮多跳预算与防环状态
    - record_hop(...)              honor 后推进状态

设计要点（D-15）：
    - v1.5 仍以 Twin 为唯一 leader，不引入 Agent 对等自由对话；
    - 多跳必须**有界 + 防环 + 预算**：max_hops 默认 3，硬顶 6；
    - 不盲从 Agent 的转交请求——A↔B 乒乓、自转交、重复转交、超预算一律拒绝。

转交指令约定（agent.md 可指示 Agent 在需要时输出，末尾生效）：
    [[handoff:<agent_id>|<理由>]]   请求把控制权转交给另一个 Agent（接力）
    [[ask:<agent_id>|<问题>]]       一次性咨询另一个 Agent（咨询后控制权回到发起方）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import get_settings

# 指令标记：[[handoff:agent_id|reason]] / [[ask:agent_id|question]]
_DIRECTIVE_RE = re.compile(r"\[\[(handoff|ask):\s*([A-Za-z0-9._\-]+)\s*\|([^\]]*)\]\]")

ACTION_HANDOFF = "handoff"
ACTION_ASK = "ask"


def parse_directive(text: str) -> dict | None:
    """从 speaker 输出解析最后一条转交/咨询指令。无则返回 None。

    取**最后一条**：Agent 可能先推理再给出最终决定。
    """
    if not text:
        return None
    matches = list(_DIRECTIVE_RE.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    return {
        "action": m.group(1),
        "to": m.group(2).strip(),
        "reason": m.group(3).strip(),
    }


def strip_directives(text: str) -> str:
    """清除全部指令标记（用于展示与落盘的干净文本）。"""
    if not text:
        return text
    return _DIRECTIVE_RE.sub("", text).strip()


@dataclass
class HopState:
    """单轮内多跳预算与防环状态。"""
    hops: int = 0
    max_hops: int = 3
    hard_cap: int = 6
    # 已出现过的 speaker 序列：[(type, id), ...]
    speaker_seq: list[tuple[str, str]] = field(default_factory=list)
    # 已发生的转交对：[(from_id, to_id), ...]
    handoff_pairs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def effective_max(self) -> int:
        """生效的多跳上限：软预算与硬顶取小，且至少 1。"""
        return max(1, min(self.max_hops, self.hard_cap))

    def budget_exhausted(self) -> bool:
        return self.hops >= self.effective_max


def new_hop_state(initial_speaker: dict | None = None) -> HopState:
    """按配置创建多跳状态。initial_speaker 计入 speaker 序列（不算一跳）。"""
    s = get_settings()
    st = HopState(max_hops=s.a2a_max_hops, hard_cap=s.a2a_hard_cap)
    if initial_speaker:
        st.speaker_seq.append((initial_speaker.get("type", ""), initial_speaker.get("id", "")))
    return st


def arbitrate_handoff(
    *,
    request: dict,
    current_speaker: dict,
    state: HopState,
    participant_agent_ids: set[str],
    known_agent_ids: set[str],
) -> dict:
    """Twin 仲裁一次转交请求（不盲从 Agent）。

    返回 {"honor": bool, "target": {type,id}|None, "reason": str, "auto_join": bool}。
    规则：自转交 / 目标不存在 / 超预算 / A↔B 乒乓 / 重复转交 → 拒绝。
    """
    to = (request or {}).get("to", "").strip()
    cur_id = current_speaker.get("id", "")

    def deny(reason: str) -> dict:
        return {"honor": False, "target": None, "reason": reason, "auto_join": False}

    if not to:
        return deny("转交目标为空")
    if to == cur_id:
        return deny("不能转交给自己")
    if to not in participant_agent_ids and to not in known_agent_ids:
        return deny(f"目标 Agent 不存在或不可用: {to}")
    if state.budget_exhausted():
        return deny(f"已达多跳预算上限（{state.effective_max} 跳）")
    # A↔B 乒乓：目标此前曾转交给当前发言者
    if (to, cur_id) in state.handoff_pairs:
        return deny("检测到 A↔B 循环转交，已拦截")
    # 重复转交：同一 from→to 不重复
    if (cur_id, to) in state.handoff_pairs:
        return deny("重复转交，已拦截")

    return {
        "honor": True,
        "target": {"type": "agent", "id": to},
        "reason": (request or {}).get("reason", ""),
        "auto_join": to not in participant_agent_ids,
    }


def record_hop(state: HopState, *, from_speaker: dict, target: dict) -> HopState:
    """honor 后推进多跳状态（+1 跳、记转交对、记新 speaker）。"""
    state.hops += 1
    state.handoff_pairs.append((from_speaker.get("id", ""), target.get("id", "")))
    state.speaker_seq.append((target.get("type", ""), target.get("id", "")))
    return state
