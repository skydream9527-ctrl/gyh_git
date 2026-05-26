from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="username or email")
    password: str


class RegisterRequest(BaseModel):
    email: str = Field(..., description="username or email; must be unique")
    name: str = Field(..., description="display name")
    password: str = Field(..., description="min 6 chars, max 128 chars")
    # 用于自动给本人加飞书文档权限的小米办公邮箱（可选）。注册时填写后，
    # feishu_publish 创建文档时会自动 perm add 给这个邮箱。后续也可在账户
    # 编辑页面修改。
    xiaomi_email: str | None = Field(default=None, description="@xiaomi.com / @mi.com")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    auth_role: str
    avatar_url: str | None = None
    feishu_bound: bool = False
    team: str | None = None
    title: str | None = None
    xiaomi_email: str | None = None


class LoginResponse(BaseModel):
    user: UserPublic
    tokens: TokenPair


class FeishuStartResponse(BaseModel):
    auth_url: str
    state: str
