"""Twin 服务：一等 Twin（用户的 AI 化身）。

存储：users/{uid}/twin/twin.json
功能：创建/读取/更新 Twin 画像 + 权限等级(L0-L5)。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.permissions import TwinLevel
from app.core.storage import paths
from app.core.storage.jsonio import read_json, write_json


_DEFAULT_TWIN = {
    "level": TwinLevel.L2_DELEGATE_DRAFT,  # 默认 L2：可起草
    "persona": "",
    "preferences": {},
    "goals": [],
}


def get_twin(uid: str) -> dict | None:
    """读取用户的 Twin 配置。"""
    return read_json(paths.twin_json(uid))


def ensure_twin(uid: str, *, name: str = "") -> dict:
    """确保 Twin 存在。首次创建使用默认配置。"""
    existing = get_twin(uid)
    if existing is not None:
        return existing

    twin = {
        "user_id": uid,
        "name": name or f"{uid} 的 Twin",
        "level": int(_DEFAULT_TWIN["level"]),
        "persona": _DEFAULT_TWIN["persona"],
        "preferences": _DEFAULT_TWIN["preferences"],
        "goals": _DEFAULT_TWIN["goals"],
        "created_at": _now_iso(),
    }
    paths.ensure(paths.twin_json(uid))
    write_json(paths.twin_json(uid), twin)
    return twin


def update_twin(
    uid: str,
    *,
    name: str | None = None,
    level: int | None = None,
    persona: str | None = None,
    preferences: dict | None = None,
    goals: list | None = None,
) -> dict:
    """更新 Twin 配置。"""
    twin = get_twin(uid)
    if twin is None:
        twin = ensure_twin(uid)

    if name is not None:
        twin["name"] = name
    if level is not None:
        _validate_level(level)
        twin["level"] = level
    if persona is not None:
        twin["persona"] = persona
    if preferences is not None:
        twin["preferences"] = preferences
    if goals is not None:
        twin["goals"] = goals

    twin["updated_at"] = _now_iso()
    write_json(paths.twin_json(uid), twin)
    return twin


def set_level(uid: str, level: int) -> dict:
    """快捷设置 Twin 权限等级。"""
    _validate_level(level)
    return update_twin(uid, level=level)


def _validate_level(level: int) -> None:
    if level < 0 or level > 5:
        raise APIError(400, ErrorCode.BAD_REQUEST, f"无效的 Twin 等级: {level}（有效: 0-5）")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
