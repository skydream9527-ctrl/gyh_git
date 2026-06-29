"""Agent 路由：列出平台可用 Agent + 详情 + 可用工具清单。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import APIError, ErrorCode, ok
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json
from app.services.tools import list_tools

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_agents(user: dict = Depends(get_current_user)) -> dict:
    """列出所有内置/团队 Agent。"""
    out = []
    for d in iter_dirs(paths.root() / "agents"):
        meta = read_json(d / "agent.json")
        if meta:
            out.append(meta)
    return ok(out)


@router.get("/tools")
def list_available_tools(user: dict = Depends(get_current_user)) -> dict:
    """列出平台内置工具清单（含风险标注）。"""
    return ok(list_tools())


@router.get("/{agent_id}")
def get_agent(agent_id: str, user: dict = Depends(get_current_user)) -> dict:
    meta = read_json(paths.agent_json(agent_id))
    if meta is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"Agent 不存在: {agent_id}")
    # 附带 agent.md
    md_path = paths.agent_md(agent_id)
    md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    return ok({**meta, "agent_md": md})
