"""认证相关 DTO。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """注册入参。"""

    email: EmailStr
    username: Optional[str] = None
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """登录入参：account 可为邮箱或用户名。"""

    account: str
    password: str


class RefreshRequest(BaseModel):
    """刷新入参。"""

    refresh_token: str


class TokenData(BaseModel):
    """token 响应数据体。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
