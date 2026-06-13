"""JWT 生成与校验（access / refresh，含 jti）。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import ErrorCode, UnauthorizedError


@dataclass
class TokenPayload:
    """解码后的 token 载荷。"""

    sub: int
    role: str
    plan: str
    jti: str
    token_type: str
    exp: int


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _create_token(
    *, user_id: int, role: str, plan: str, ttl: int, token_type: str
) -> str:
    settings = get_settings()
    issued = _now()
    payload = {
        "sub": str(user_id),
        "role": role,
        "plan": plan,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(*, user_id: int, role: str, plan: str) -> str:
    """生成短期 access token。"""
    settings = get_settings()
    return _create_token(
        user_id=user_id,
        role=role,
        plan=plan,
        ttl=settings.jwt_access_ttl,
        token_type="access",
    )


def create_refresh_token(*, user_id: int, role: str, plan: str) -> str:
    """生成长期 refresh token。"""
    settings = get_settings()
    return _create_token(
        user_id=user_id,
        role=role,
        plan=plan,
        ttl=settings.jwt_refresh_ttl,
        token_type="refresh",
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> TokenPayload:
    """解码并校验 token；过期或非法抛 UnauthorizedError。"""
    settings = get_settings()
    try:
        raw = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise UnauthorizedError("token 无效或已过期") from exc

    token_type = raw.get("type", "")
    if expected_type and token_type != expected_type:
        raise UnauthorizedError(
            "token 类型不匹配", code=ErrorCode.UNAUTHORIZED
        )

    try:
        return TokenPayload(
            sub=int(raw["sub"]),
            role=raw.get("role", "user"),
            plan=raw.get("plan", "free"),
            jti=raw["jti"],
            token_type=token_type,
            exp=int(raw["exp"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise UnauthorizedError("token 载荷非法") from exc
