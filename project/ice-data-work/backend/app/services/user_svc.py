"""用户服务：CRUD + 首登自动建号。

存储：users/{uid}/profile.json（G3 文件优先）。
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import APIError, ErrorCode
from app.core.security import hash_password
from app.core.storage import paths
from app.core.storage.jsonio import iter_dirs, read_json, write_json


def get_user(uid: str) -> dict | None:
    """读取用户信息（不含密码哈希）。"""
    profile = read_json(paths.user_profile(uid))
    if profile is None:
        return None
    return {k: v for k, v in profile.items() if k != "password_hash"}


def ensure_user(uid: str, *, name: str = "", platform_role: str = "user") -> dict:
    """确保用户存在（首登自动建号）。返回用户信息。"""
    existing = read_json(paths.user_profile(uid))
    if existing is not None:
        return {k: v for k, v in existing.items() if k != "password_hash"}

    profile = {
        "id": uid,
        "name": name or uid,
        "platform_role": platform_role,
        "password_hash": "",  # OAuth/Aegis 用户无密码
        "created_at": _now_iso(),
    }
    paths.ensure(paths.user_profile(uid))
    write_json(paths.user_profile(uid), profile)

    # 自动创建个人项目（M1-T06）
    _auto_create_personal_project(uid)

    return {k: v for k, v in profile.items() if k != "password_hash"}


def create_user(
    uid: str, *, name: str = "", password: str = "", platform_role: str = "user"
) -> dict:
    """创建用户（带密码）。已存在则报冲突。"""
    if read_json(paths.user_profile(uid)) is not None:
        raise APIError(409, ErrorCode.CONFLICT, f"用户已存在: {uid}")

    profile = {
        "id": uid,
        "name": name or uid,
        "platform_role": platform_role,
        "password_hash": hash_password(password) if password else "",
        "created_at": _now_iso(),
    }
    paths.ensure(paths.user_profile(uid))
    write_json(paths.user_profile(uid), profile)

    # 自动创建个人项目
    _auto_create_personal_project(uid)

    return {k: v for k, v in profile.items() if k != "password_hash"}


def update_user(uid: str, *, name: str | None = None, platform_role: str | None = None) -> dict:
    """更新用户资料（仅可修改 name / platform_role）。"""
    profile = read_json(paths.user_profile(uid))
    if profile is None:
        raise APIError(404, ErrorCode.NOT_FOUND, f"用户不存在: {uid}")

    if name is not None:
        profile["name"] = name
    if platform_role is not None:
        profile["platform_role"] = platform_role
    profile["updated_at"] = _now_iso()

    write_json(paths.user_profile(uid), profile)
    return {k: v for k, v in profile.items() if k != "password_hash"}


def list_users() -> list[dict]:
    """列出所有用户（遍历 users/ 目录）。"""
    out: list[dict] = []
    for d in iter_dirs(paths.root() / "users"):
        profile = read_json(d / "profile.json")
        if profile:
            out.append({k: v for k, v in profile.items() if k != "password_hash"})
    return out


def _auto_create_personal_project(uid: str) -> None:
    """自动创建用户的个人团队 + 个人项目（M1-T06）。

    个人团队 ID = "personal_{uid}"，个人项目 ID = "p_personal_{uid}"。
    """
    personal_team_id = f"personal_{uid}"
    personal_project_id = f"p_personal_{uid}"

    # 个人团队
    tj = paths.team_json(personal_team_id)
    if read_json(tj) is None:
        paths.ensure(tj)
        write_json(tj, {
            "id": personal_team_id,
            "name": f"{uid} 的个人空间",
            "type": "personal",
            "members": [{"user_id": uid, "role": "owner"}],
            "created_at": _now_iso(),
        })

    # 个人项目
    pj = paths.project_json(personal_team_id, personal_project_id)
    if read_json(pj) is None:
        paths.ensure(pj)
        write_json(pj, {
            "id": personal_project_id,
            "team_id": personal_team_id,
            "name": "个人项目",
            "type": "personal",
            "members": [{"user_id": uid, "role": "owner"}],
            "created_at": _now_iso(),
        })


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
