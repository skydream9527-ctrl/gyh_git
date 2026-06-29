"""FastAPI 依赖注入：当前用户 + 权限校验。

用法：
    @router.get("/protected")
    def endpoint(user: dict = Depends(get_current_user)):
        ...

    @router.post("/admin-only")
    def endpoint(user: dict = Depends(require_role("admin"))):
        ...

    @router.get("/teams/{team_id}/data")
    def endpoint(team_id: str, user: dict = Depends(require_member("team_id"))):
        ...
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from fastapi import Depends, Header, Request
from jose import JWTError

from app.core.errors import APIError, ErrorCode
from app.core.permissions import MemberRole, PlatformRole
from app.core.security import decode_access_token, verify_aegis_header
from app.core.storage import paths
from app.core.storage.jsonio import read_json


def get_current_user(
    authorization: str = Header(default=""),
    x_aegis_user: str = Header(default="", alias="X-Aegis-User"),
) -> dict:
    """解析当前用户。优先 Aegis 头（内网网关），其次 Bearer JWT。"""
    # 尝试 Aegis 头
    aegis_uid = verify_aegis_header(x_aegis_user)
    if aegis_uid:
        profile = read_json(paths.user_profile(aegis_uid))
        if profile:
            return {k: v for k, v in profile.items() if k != "password_hash"}
        raise APIError(401, ErrorCode.UNAUTHORIZED, "Aegis 用户不存在")

    # Bearer JWT
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "未提供认证凭据")

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "Token 无效或已过期")

    uid = payload.get("sub", "")
    if not uid:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "Token 缺少 sub 字段")

    profile = read_json(paths.user_profile(uid))
    if profile is None:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "用户不存在")

    safe = {k: v for k, v in profile.items() if k != "password_hash"}
    safe["_token_payload"] = payload  # 方便下游取 role/exp 等
    return safe


def require_role(*roles: str) -> Callable:
    """要求平台角色（super_admin / admin / user）。"""

    def _dep(user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("platform_role", "user")
        if user_role not in roles:
            raise APIError(403, ErrorCode.FORBIDDEN, f"需要角色: {', '.join(roles)}")
        return user

    return _dep


def require_member(path_param: str = "team_id", min_role: str = MemberRole.MEMBER) -> Callable:
    """要求用户是指定团队/项目的成员。

    从路由 path 参数获取 team_id，检查 team.json 的 members 列表。
    平台管理员始终通过。
    """
    role_order = [MemberRole.MEMBER, MemberRole.ADMIN, MemberRole.OWNER]

    def _dep(request: Request, user: dict = Depends(get_current_user)) -> dict:
        # 平台管理员跳过成员检查
        if user.get("platform_role") in (PlatformRole.SUPER_ADMIN, PlatformRole.ADMIN):
            return user

        resource_id = request.path_params.get(path_param, "")
        if not resource_id:
            raise APIError(400, ErrorCode.BAD_REQUEST, f"缺少路径参数: {path_param}")

        # 读取团队元数据
        team_meta = read_json(paths.team_json(resource_id))
        if team_meta is None:
            raise APIError(404, ErrorCode.NOT_FOUND, f"团队不存在: {resource_id}")

        uid = user.get("id", "")
        members = team_meta.get("members", [])
        member_entry = next((m for m in members if m.get("user_id") == uid), None)

        if member_entry is None:
            raise APIError(403, ErrorCode.FORBIDDEN, "非团队成员，无权访问")

        # 检查最低角色
        member_role = member_entry.get("role", MemberRole.MEMBER)
        if role_order.index(member_role) < role_order.index(min_role):
            raise APIError(403, ErrorCode.FORBIDDEN, f"需要至少 {min_role} 角色")

        user["_member_role"] = member_role
        return user

    return _dep


# 快捷依赖
CurrentUser = Depends(get_current_user)
AdminOnly = Depends(require_role(PlatformRole.SUPER_ADMIN, PlatformRole.ADMIN))
