"""认证服务：登录（用户名密码）、飞书 OAuth placeholder、Token 刷新。

登录策略：
1. 用户名 + 密码（本地账号）
2. 飞书 OAuth（M1 placeholder，后续对接）
3. Aegis 头（网关注入，仅限内网部署）

首次登录自动建号逻辑由 user_svc.ensure_user() 完成。
"""
from __future__ import annotations

from app.core.errors import APIError, ErrorCode
from app.core.security import create_access_token, hash_password, verify_password
from app.core.storage import paths
from app.core.storage.jsonio import read_json, write_json


def login(username: str, password: str) -> dict:
    """用户名密码登录。成功返回 {token, user}。"""
    profile = read_json(paths.user_profile(username))
    if profile is None:
        raise APIError(401, ErrorCode.UNAUTHORIZED, "用户不存在或密码错误")

    stored_hash = profile.get("password_hash", "")
    if not stored_hash or not verify_password(password, stored_hash):
        raise APIError(401, ErrorCode.UNAUTHORIZED, "用户不存在或密码错误")

    token = create_access_token(
        subject=profile["id"],
        extra={"role": profile.get("platform_role", "user")},
    )
    return {
        "token": token,
        "user": _safe_user(profile),
    }


def register(username: str, password: str, name: str = "") -> dict:
    """注册本地账号。如已存在则报冲突。"""
    if read_json(paths.user_profile(username)) is not None:
        raise APIError(409, ErrorCode.CONFLICT, f"用户已存在: {username}")

    profile = {
        "id": username,
        "name": name or username,
        "platform_role": "user",
        "password_hash": hash_password(password),
        "created_at": _now_iso(),
    }
    paths.ensure(paths.user_profile(username))
    write_json(paths.user_profile(username), profile)
    token = create_access_token(subject=username, extra={"role": "user"})
    return {"token": token, "user": _safe_user(profile)}


def feishu_oauth_callback(code: str) -> dict:
    """飞书 OAuth 回调（placeholder）。

    真实实现：用 code 换 access_token → 获取用户信息 → ensure_user → 签 JWT。
    """
    from app.core.config import get_settings

    if not get_settings().feishu_app_id:
        raise APIError(501, ErrorCode.FEISHU_NOT_CONFIGURED, "飞书 OAuth 未配置")
    # TODO: 实现飞书 OAuth 流程
    raise APIError(501, ErrorCode.FEISHU_NOT_CONFIGURED, "飞书 OAuth 尚未实现")


def _safe_user(profile: dict) -> dict:
    """剔除密码哈希，返回安全的用户信息。"""
    return {k: v for k, v in profile.items() if k != "password_hash"}


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
