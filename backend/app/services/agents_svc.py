"""Agents and Skills exposed via filesystem under agents/ and skills/."""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ..core.errors import APIError, ErrorCode
from ..core.storage import get_paths, read_json, write_json


# Agents seeded at boot — tasks/admin UI rely on these being present, so we
# refuse to delete them (the seed loop would silently recreate them on next
# boot and the audit trail would be confusing).
PROTECTED_AGENT_IDS = {"biz-insight", "ab-experiment", "wave-attribution", "data-analysis", "gray-release", "know"}

_AGENT_ID_RE = re.compile(r"^[a-z][a-z0-9\-]{2,40}$")

_DEFAULT_AGENTS = [
    {
        "id": "biz-insight",
        "name": "经营洞察 Agent",
        "paradigm": "biz",
        "icon": "📈",
        "color": "#d4a34e",
        "description": "待上线，敬请期待",
        "publish_status": "coming_soon",
        "system_prompt": (
            "你是一名专业的经营分析 Agent，帮助产品团队从经营数据中发现关键洞察。\n\n"
            "核心原则：\n"
            "1. 数据查询必须先确认指标口径\n"
            "2. 渠道归因优先检查自然流量与推荐渠道的版本影响\n"
            "3. 季度报告必须包含同比和环比"
        ),
    },
    {
        "id": "ab-experiment",
        "name": "实验分析 Agent",
        "paradigm": "ab",
        "icon": "⚖",
        "color": "#7bafd4",
        "description": "AB 显著性 · 下钻 · 放量决策",
        "publish_status": "published",
        "system_prompt": "你是一名 AB 实验分析专家，遵循统计严谨的标准。",
    },
    {
        "id": "wave-attribution",
        "name": "波动归因 Agent",
        "paradigm": "wave",
        "icon": "🔥",
        "color": "#c97b7b",
        "description": "待上线，敬请期待",
        "publish_status": "coming_soon",
        "system_prompt": "你是一名指标异常归因专家，按渠道、版本、地域等维度逐层下钻。",
    },
    {
        "id": "data-analysis",
        "name": "数据分析 Agent",
        "paradigm": "data",
        "icon": "📊",
        "color": "#6baa8e",
        "description": "NL→SQL · Kyuubi 查询 · 自动出报告",
        "publish_status": "published",
        "system_prompt": "你是一名 NL→SQL 助手，写完 SQL 后再做可视化建议。",
    },
    {
        "id": "gray-release",
        "name": "灰度版本 Agent",
        "paradigm": "gray",
        "icon": "🌐",
        "color": "#9b8ec4",
        "description": "版本灰度 SOP · 决策矩阵 · AI 下钻 · 放量决策（V1.2）",
        "publish_status": "published",
        "system_prompt": "你是一名 APP 版本灰度发布数据分析专家（V1.2），按对照包 vs 业务包模式分析（分组依据 app_version，通常免 AA）。严格按六阶段 SOP 推进。",
    },
    {
        "id": "know",
        "name": "知识库 Agent",
        "paradigm": "knowledge",
        "icon": "📚",
        "color": "#b6a07c",
        "description": "飞书 + Mify 知识库语义检索与同步",
        "publish_status": "published",
        "system_prompt": (
            "你是一名知识库管理 Agent，负责连接和管理飞书知识库与 Mify RAG 知识库。"
        ),
    },
]


def _ensure_seed_agents() -> None:
    paths = get_paths()
    paths.agents.mkdir(parents=True, exist_ok=True)
    for a in _DEFAULT_AGENTS:
        d = paths.agents / a["id"]
        d.mkdir(parents=True, exist_ok=True)
        cfg_path = d / "agent.json"
        if not cfg_path.exists():
            from ..core.storage import write_json

            write_json(cfg_path, a)
        prompt_dir = d / "prompt"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        sp_path = prompt_dir / "system.md"
        if not sp_path.exists():
            sp_path.write_text(a.get("system_prompt", ""), encoding="utf-8")


def list_agents() -> list[dict]:
    _ensure_seed_agents()
    paths = get_paths()
    out: list[dict] = []
    if not paths.agents.exists():
        return out
    for d in sorted(paths.agents.iterdir()):
        if not d.is_dir():
            continue
        cfg = read_json(d / "agent.json")
        if cfg:
            out.append(cfg)
    return out


def get_agent(agent_id: str) -> dict | None:
    _ensure_seed_agents()
    cfg = read_json(get_paths().agents / agent_id / "agent.json")
    return cfg


def get_agent_system_prompt(agent_id: str) -> str:
    _ensure_seed_agents()
    md_path: Path = get_paths().agents / agent_id / "prompt" / "system.md"
    if md_path.exists():
        return md_path.read_text(encoding="utf-8")
    cfg = get_agent(agent_id) or {}
    return cfg.get("system_prompt", "你是一名通用 AI 助手。")


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def count_tasks_using_agent(agent_id: str) -> int:
    """Count active (non-archived) tasks bound to this agent. Uses the SQLite
    index for speed; falls back to scanning `tasks/` if the index is empty."""
    from ..core.storage import get_index_db

    db = get_index_db()
    row = await db.fetchone(
        "SELECT COUNT(*) AS c FROM tasks_index WHERE agent_id = ?", [agent_id]
    )
    if row:
        return int(row.get("c", 0))
    # Fallback: manual scan (rare — only when the index hasn't been built yet).
    paths = get_paths()
    if not paths.tasks.exists():
        return 0
    n = 0
    for d in paths.tasks.iterdir():
        meta = read_json(d / "meta.json") if d.is_dir() else None
        if isinstance(meta, dict) and meta.get("agent_id") == agent_id:
            n += 1
    return n


def create_agent(
    *,
    agent_id: str,
    name: str,
    paradigm: str,
    icon: str = "🤖",
    color: str = "#7bafd4",
    description: str = "",
    system_prompt: str = "",
    publish_status: str = "draft",
) -> dict:
    """Create a new agent directory + agent.json + prompt/system.md.

    Validates id format (3-40 chars, lowercase + digits + dashes, must start
    with a letter) and uniqueness. Raises APIError on validation failure.
    Returns the newly written agent config dict.
    """
    aid = (agent_id or "").strip()
    if not _AGENT_ID_RE.match(aid):
        raise APIError(
            400,
            ErrorCode.VALIDATION_ERROR,
            "agent_id 必须以小写字母开头，3-41 位，仅允许小写字母/数字/短横线",
        )
    if not (name or "").strip():
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "name 不能为空")
    if not (paradigm or "").strip():
        raise APIError(400, ErrorCode.VALIDATION_ERROR, "paradigm 不能为空")
    if publish_status not in ("draft", "published", "coming_soon", "archived"):
        raise APIError(400, ErrorCode.VALIDATION_ERROR, f"publish_status 非法：{publish_status}")

    paths = get_paths()
    agent_dir = paths.agents / aid
    if agent_dir.exists():
        raise APIError(409, ErrorCode.VALIDATION_ERROR, f"agent_id `{aid}` 已存在")

    cfg = {
        "id": aid,
        "name": name.strip(),
        "paradigm": paradigm.strip(),
        "icon": (icon or "🤖").strip() or "🤖",
        "color": (color or "#7bafd4").strip() or "#7bafd4",
        "description": (description or "").strip(),
        "publish_status": publish_status,
        "system_prompt": system_prompt or "",
        "created_at": _now(),
    }
    agent_dir.mkdir(parents=True, exist_ok=True)
    write_json(agent_dir / "agent.json", cfg)
    prompt_dir = agent_dir / "prompt"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "system.md").write_text(system_prompt or "", encoding="utf-8")
    # cards.md starts empty — experience_card_svc rebuilds it on first approval.
    (prompt_dir / "cards.md").write_text("", encoding="utf-8")
    return cfg


async def delete_agent(*, agent_id: str, force: bool = False) -> dict:
    """Remove agents/<agent_id>/ and return {removed: True, tasks_orphaned: N}.

    Guards:
        - Protected seed agents cannot be deleted (PROTECTED_AGENT_IDS).
        - If any task references this agent, raises unless force=True.

    When force=True the agent folder is wiped but existing tasks keep a copy of
    the agent via their per-task snapshot (tasks/{tid}/agent/agent.json), so
    they continue working; only NEW tasks cannot select this agent.
    """
    aid = (agent_id or "").strip().lower()
    paths = get_paths()
    agent_dir = paths.agents / aid
    if not agent_dir.exists():
        raise APIError(404, ErrorCode.RESOURCE_NOT_FOUND, f"agent `{aid}` 不存在")
    if aid in PROTECTED_AGENT_IDS:
        raise APIError(
            400,
            ErrorCode.VALIDATION_ERROR,
            f"`{aid}` 是系统预置 Agent，不可删除（会被种子逻辑重建）",
        )
    in_use = await count_tasks_using_agent(aid)
    if in_use and not force:
        raise APIError(
            409,
            ErrorCode.VALIDATION_ERROR,
            f"该 Agent 仍被 {in_use} 个任务引用；如需强制删除请传 force=true（任务会继续用各自的快照）",
        )
    shutil.rmtree(agent_dir)
    return {"removed": True, "tasks_orphaned": in_use}


def list_skills() -> list[dict]:
    """Builtin tool descriptors are exposed as Skills for now."""
    from .tool_runner import BUILTIN_TOOL_SCHEMAS

    return [
        {
            "id": t["function"]["name"],
            "name": t["_meta"]["display_name"],
            "description": t["function"]["description"],
            "category": "builtin",
            "tool_entry": "app.services.tool_runner:" + t["function"]["name"],
            "tool_schema": t["function"],
        }
        for t in BUILTIN_TOOL_SCHEMAS
    ]
