"""用户路由：列表 / 查看 / 更新（需管理员权限管理他人）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user, require_role
from app.core.errors import ok
from app.core.permissions import PlatformRole
from app.services import user_svc

router = APIRouter(prefix="/users", tags=["users"])


class UpdateUserReq(BaseModel):
    name: str | None = None
    platform_role: str | None = None


@router.get("")
def list_users(
    user: dict = Depends(require_role(PlatformRole.SUPER_ADMIN, PlatformRole.ADMIN)),
) -> dict:
    """列出所有用户（仅管理员）。"""
    return ok(user_svc.list_users())


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)) -> dict:
    """获取当前用户信息。"""
    return ok({k: v for k, v in user.items() if not k.startswith("_")})


@router.get("/{uid}")
def get_user(uid: str, user: dict = Depends(get_current_user)) -> dict:
    """查看用户信息。"""
    result = user_svc.get_user(uid)
    if result is None:
        from app.core.errors import APIError, ErrorCode
        raise APIError(404, ErrorCode.NOT_FOUND, f"用户不存在: {uid}")
    return ok(result)


@router.put("/{uid}")
def update_user(
    uid: str,
    body: UpdateUserReq,
    user: dict = Depends(get_current_user),
) -> dict:
    """更新用户信息。仅自己或管理员可修改。"""
    from app.core.errors import APIError, ErrorCode

    is_self = user.get("id") == uid
    is_admin = user.get("platform_role") in (PlatformRole.SUPER_ADMIN, PlatformRole.ADMIN)
    if not is_self and not is_admin:
        raise APIError(403, ErrorCode.FORBIDDEN, "只能修改自己的信息")

    # 非管理员不能改 platform_role
    role = body.platform_role if is_admin else None
    result = user_svc.update_user(uid, name=body.name, platform_role=role)
    return ok(result)
