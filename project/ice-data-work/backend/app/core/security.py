"""JWT 签发/验证 + 密码哈希。

- 签发：HS256，包含 sub(user_id) + exp + role
- 验证：解码 + 过期检查
- 密码：bcrypt 直接调用
- Aegis：米盾头校验（M1 placeholder，后续接真实网关）
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    subject: str,
    *,
    extra: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """签发 JWT。subject 通常为 user_id。"""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "iat": now, "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """解码 JWT，失败抛 JWTError。"""
    return jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])


def verify_aegis_header(header_value: str | None) -> str | None:
    """米盾网关头校验（placeholder）。

    生产环境由反代注入 X-Aegis-User，此处信任该头。
    返回 user_id 或 None（未配置/无头）。
    """
    if not header_value:
        return None
    # 生产中：反代已验证签名，直接信任 header
    return header_value.strip() or None
