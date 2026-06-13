"""鉴权依赖：解析 JWT / API Key 为 Principal，并提供角色/作用域守卫。

注：为满足「get_current_user 依赖位于 core/security」的设计要求，本模块需访问
users 模块的 ORM 模型。为避免 core 与 features 的导入环，所有对 features 的引用
均采用函数内惰性导入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache
from app.core.db import get_session
from app.core.errors import ErrorCode, ForbiddenError, UnauthorizedError
from app.core.security.api_key import parse_api_key, verify_api_key_secret
from app.core.security.jwt import decode_token

ALL_SCOPES = "*"


@dataclass
class Principal:
    """当前请求主体（用户身份 + 鉴权来源）。"""

    user_id: int
    role: str
    plan: str
    scopes: List[str] = field(default_factory=list)
    auth_type: str = "jwt"  # jwt | api_key
    jti: Optional[str] = None
    api_key_id: Optional[int] = None

    def has_scope(self, scope: str) -> bool:
        """是否具备指定作用域（JWT 用户拥有全部作用域）。"""
        return ALL_SCOPES in self.scopes or scope in self.scopes


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise UnauthorizedError("缺少 Bearer 凭证")
    token = auth[len("Bearer ") :].strip()
    if not token:
        raise UnauthorizedError("缺少 Bearer 凭证")
    return token


async def _principal_from_api_key(token: str, session: AsyncSession) -> Principal:
    from app.features.users.models import ApiKey, User

    parsed = parse_api_key(token)
    if parsed is None:
        raise UnauthorizedError("API Key 格式非法", code=ErrorCode.API_KEY_INVALID)

    api_key = (
        await session.execute(select(ApiKey).where(ApiKey.prefix == parsed.prefix))
    ).scalar_one_or_none()
    if api_key is None or api_key.status != "active":
        raise UnauthorizedError("API Key 无效或已吊销", code=ErrorCode.API_KEY_INVALID)
    if not verify_api_key_secret(parsed.secret, api_key.key_hash):
        raise UnauthorizedError("API Key 无效或已吊销", code=ErrorCode.API_KEY_INVALID)

    user = (
        await session.execute(select(User).where(User.id == api_key.user_id))
    ).scalar_one_or_none()
    if user is None or user.status != "active":
        raise UnauthorizedError("用户不存在或已禁用")

    scopes = [s for s in (api_key.scopes or "").replace(",", " ").split() if s]
    return Principal(
        user_id=user.id,
        role=user.role,
        plan=user.plan,
        scopes=scopes,
        auth_type="api_key",
        api_key_id=api_key.id,
    )


async def _principal_from_jwt(token: str, session: AsyncSession) -> Principal:
    from app.features.users.models import User

    payload = decode_token(token, expected_type="access")
    cache = get_cache()
    if await cache.is_blacklisted(payload.jti):
        raise UnauthorizedError("登录已失效，请重新登录")

    user = (
        await session.execute(select(User).where(User.id == payload.sub))
    ).scalar_one_or_none()
    if user is None or user.status != "active":
        raise UnauthorizedError("用户不存在或已禁用")

    return Principal(
        user_id=user.id,
        role=user.role,
        plan=user.plan,
        scopes=[ALL_SCOPES],
        auth_type="jwt",
        jti=payload.jti,
    )


async def get_current_principal(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Principal:
    """解析当前请求主体：支持 JWT 与 API Key 两种 Bearer 凭证。"""
    token = _extract_bearer(request)
    if token.startswith("wsq_"):
        return await _principal_from_api_key(token, session)
    return await _principal_from_jwt(token, session)


def require_role(role: str):
    """生成角色守卫依赖：admin 始终放行。"""

    async def _guard(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role != role and principal.role != "admin":
            raise ForbiddenError("角色权限不足", code=ErrorCode.FORBIDDEN_ROLE)
        return principal

    return _guard


def require_scopes(*needed: str):
    """生成作用域守卫依赖：缺少任一作用域返回 40302。"""

    async def _guard(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        for scope in needed:
            if not principal.has_scope(scope):
                raise ForbiddenError(
                    f"缺少作用域: {scope}", code=ErrorCode.FORBIDDEN_ROLE
                )
        return principal

    return _guard


async def require_user_session(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """要求 JWT 用户会话：禁止 API Key 进行密钥自管理等敏感操作。"""
    if principal.auth_type != "jwt":
        raise ForbiddenError(
            "该操作需用户登录会话，API Key 不可执行",
            code=ErrorCode.FORBIDDEN_ROLE,
        )
    return principal
