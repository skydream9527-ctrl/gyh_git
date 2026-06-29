"""认证路由：登录 / 注册 / 当前用户信息。"""
from __future__ import annotations

from fastapi import APIRouter, Header
from pydantic import BaseModel

from app.core.errors import ok
from app.services import auth_svc

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginReq(BaseModel):
    username: str
    password: str


class RegisterReq(BaseModel):
    username: str
    password: str
    name: str = ""


@router.post("/login")
def login(body: LoginReq) -> dict:
    result = auth_svc.login(body.username, body.password)
    return ok(result)


@router.post("/register")
def register(body: RegisterReq) -> dict:
    result = auth_svc.register(body.username, body.password, body.name)
    return ok(result)


@router.get("/me")
def me(authorization: str = Header(default="")) -> dict:
    """获取当前用户信息（需 Bearer token）。"""
    from app.core.security import decode_access_token
    from app.core.storage import paths
    from app.core.storage.jsonio import read_json
    from app.core.errors import APIError, ErrorCode
    from jose import JWTError

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "未提供认证 Token")
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "Token 无效或已过期")

    uid = payload.get("sub", "")
    profile = read_json(paths.user_profile(uid))
    if profile is None:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "用户不存在")

    safe = {k: v for k, v in profile.items() if k != "password_hash"}
    return ok(safe)


@router.post("/feishu/callback")
def feishu_callback(code: str = "") -> dict:
    """飞书 OAuth 回调（placeholder）。"""
    result = auth_svc.feishu_oauth_callback(code)
    return ok(result)
