"""管理后台路由：概览统计 / 用户管理 / 团队项目 / 用量 / 系统设置（admin gate）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import require_role
from app.core.errors import ok
from app.core.permissions import PlatformRole
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json
from app.services import control_svc, usage_svc, user_svc

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN = require_role(PlatformRole.SUPER_ADMIN, PlatformRole.ADMIN)
_SUPER = require_role(PlatformRole.SUPER_ADMIN)


class RoleReq(BaseModel):
    platform_role: str


@router.get("/overview")
def overview(user: dict = Depends(_ADMIN)) -> dict:
    """后台概览统计。"""
    users = _count_dirs("users")
    teams_list = list(iter_dirs(paths.root() / "teams"))
    projects = 0
    for t in teams_list:
        projects += len(list(iter_dirs(t / "projects")))
    agents = _count_dirs("agents")
    tasks = _count_dirs("tasks")
    usage = usage_svc.summary()
    return ok({
        "users": users,
        "teams": len([t for t in teams_list if not t.name.startswith("personal_")]),
        "projects": projects,
        "agents": agents,
        "tasks": tasks,
        "total_tokens": usage["total_tokens"],
        "total_cost_usd": usage["total_cost_usd"],
        "global_paused": control_svc.is_paused(),
    })


@router.get("/users")
def list_users(user: dict = Depends(_ADMIN)) -> dict:
    return ok(user_svc.list_users())


@router.put("/users/{uid}/role")
def set_role(uid: str, body: RoleReq, user: dict = Depends(_SUPER)) -> dict:
    """变更平台角色（仅 super_admin）。"""
    result = user_svc.update_user(uid, platform_role=body.platform_role)
    return ok(result)


@router.get("/teams")
def list_teams(user: dict = Depends(_ADMIN)) -> dict:
    """列出所有团队（含成员/项目数）。"""
    out = []
    for d in iter_dirs(paths.root() / "teams"):
        if d.name.startswith("personal_"):
            continue
        meta = read_json(d / "team.json")
        if meta:
            out.append({
                "id": meta.get("id"),
                "name": meta.get("name"),
                "member_count": len(meta.get("members", [])),
                "project_count": len(list(iter_dirs(d / "projects"))),
            })
    return ok(out)


@router.get("/usage")
def usage(month: str | None = None, user: dict = Depends(_ADMIN)) -> dict:
    return ok(usage_svc.summary(month=month))


@router.get("/settings")
def settings(user: dict = Depends(_ADMIN)) -> dict:
    """系统设置 / 集成状态（只读快照）。"""
    from app.core.config import get_settings
    s = get_settings()
    return ok({
        "llm_enabled": s.llm_enabled,
        "pgvector_enabled": s.pgvector_enabled,
        "feishu_configured": bool(s.feishu_app_id),
        "kyuubi_configured": bool(s.kyuubi_host),
        "features": {
            "twin": s.twin_enabled,
            "self_evolve": s.self_evolve_enabled,
            "daemon": s.daemon_enabled,
            "cross_twin": s.cross_twin_enabled,
        },
    })


def _count_dirs(top: str) -> int:
    return len(list(iter_dirs(paths.root() / top)))
