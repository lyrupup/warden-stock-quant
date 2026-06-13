"""认证业务编排：注册、登录（限速）、刷新、登出。"""

from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.errors import (
    ConflictError,
    RateLimitedError,
    UnauthorizedError,
    ValidationFailedError,
)
from app.core.security.deps import Principal
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.security.password import hash_password, verify_password
from app.features.auth.schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenData,
)
from app.features.users.models import User
from app.features.users.repository import UserRepository


class AuthService:
    """认证服务。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._settings = get_settings()
        self._cache = get_cache()

    def _issue_tokens(self, user: User) -> TokenData:
        access = create_access_token(
            user_id=user.id, role=user.role, plan=user.plan
        )
        refresh = create_refresh_token(
            user_id=user.id, role=user.role, plan=user.plan
        )
        return TokenData(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=self._settings.jwt_access_ttl,
        )

    async def register(self, payload: RegisterRequest) -> TokenData:
        email = str(payload.email).lower().strip()
        if await self._users.get_by_email(email) is not None:
            raise ConflictError("邮箱已被注册")
        if payload.username:
            if await self._users.get_by_username(payload.username) is not None:
                raise ConflictError("用户名已被占用")

        user = User(
            email=email,
            username=payload.username,
            password_hash=hash_password(payload.password),
            role="user",
            plan="free",
            status="active",
            live_enabled=False,
        )
        await self._users.add(user)
        await self._users.ensure_quota(user.id)
        return self._issue_tokens(user)

    async def login(self, payload: LoginRequest) -> TokenData:
        account = payload.account.strip()
        if not account or not payload.password:
            raise ValidationFailedError("账号或密码不能为空")

        fail_key = f"login:fail:{account.lower()}"
        current = await self._cache.get_int(fail_key)
        if current >= self._settings.login_fail_max:
            raise RateLimitedError("登录失败次数过多，请稍后再试")

        user = await self._users.get_by_account(account)
        if user is None or not verify_password(payload.password, user.password_hash):
            attempts = await self._cache.incr_with_ttl(
                fail_key, self._settings.login_fail_window
            )
            if attempts >= self._settings.login_fail_max:
                raise RateLimitedError("登录失败次数过多，请稍后再试")
            raise UnauthorizedError("账号或密码错误")

        if user.status != "active":
            raise UnauthorizedError("账号已被禁用")

        await self._cache.delete(fail_key)
        return self._issue_tokens(user)

    async def refresh(self, payload: RefreshRequest) -> TokenData:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
        if await self._cache.is_blacklisted(token_payload.jti):
            raise UnauthorizedError("refresh token 已失效")

        user = await self._users.get_by_id(token_payload.sub)
        if user is None or user.status != "active":
            raise UnauthorizedError("用户不存在或已禁用")

        # 轮换：吊销旧 refresh token 的 jti。
        ttl = max(token_payload.exp - int(time.time()), 1)
        await self._cache.add_to_blacklist(token_payload.jti, ttl)
        return self._issue_tokens(user)

    async def logout(self, principal: Principal) -> None:
        """将当前 access token 的 jti 加入黑名单。"""
        if principal.auth_type == "jwt" and principal.jti:
            await self._cache.add_to_blacklist(
                principal.jti, self._settings.jwt_access_ttl
            )
