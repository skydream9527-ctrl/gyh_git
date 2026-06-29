"""Twin 路由：查看 / 更新当前用户的 Twin 配置 + 记忆管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.errors import ok
from app.core.storage import paths
from app.services import memory_svc, twin_svc

router = APIRouter(prefix="/twin", tags=["twin"])


class UpdateTwinReq(BaseModel):
    name: str | None = None
    level: int | None = None
    persona: str | None = None
    preferences: dict | None = None
    goals: list | None = None


@router.get("")
def get_my_twin(user: dict = Depends(get_current_user)) -> dict:
    """获取当前用户的 Twin（不存在则自动创建）。"""
    twin = twin_svc.ensure_twin(user["id"], name=user.get("name", ""))
    return ok(twin)


@router.put("")
def update_my_twin(body: UpdateTwinReq, user: dict = Depends(get_current_user)) -> dict:
    """更新 Twin 配置（画像/等级/偏好/目标）。"""
    result = twin_svc.update_twin(
        user["id"],
        name=body.name,
        level=body.level,
        persona=body.persona,
        preferences=body.preferences,
        goals=body.goals,
    )
    return ok(result)


@router.put("/level")
def set_twin_level(level: int, user: dict = Depends(get_current_user)) -> dict:
    """快捷设置 Twin 权限等级（L0-L5）。"""
    result = twin_svc.set_level(user["id"], level)
    return ok(result)


@router.get("/memory")
def get_twin_memory(user: dict = Depends(get_current_user)) -> dict:
    """读取当前用户 Twin 的记忆条目（偏好 + pinned），供 Twin Manager 管理。"""
    uid = user["id"]
    mem_dir = paths.twin_dir(uid) / "memory"
    out: dict[str, list] = {"preferences": [], "pinned": []}
    out["preferences"] = memory_svc.read_memory_entries(mem_dir / "preferences.memory.md")
    out["pinned"] = memory_svc.read_memory_entries(mem_dir / "pinned.memory.md")
    return ok(out)
