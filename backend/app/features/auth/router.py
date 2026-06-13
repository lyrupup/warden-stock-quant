"""认证路由（/auth/*）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import success
from app.core.security.deps import Principal, get_current_principal
from app.features.auth.schema import LoginRequest, RefreshRequest, RegisterRequest
from app.features.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", summary="用户注册")
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await AuthService(session).register(payload)
    return success(tokens.model_dump(), message="注册成功")


@router.post("/login", summary="登录（JWT）")
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await AuthService(session).login(payload)
    return success(tokens.model_dump(), message="登录成功")


@router.post("/refresh", summary="刷新 token")
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    tokens = await AuthService(session).refresh(payload)
    return success(tokens.model_dump(), message="刷新成功")


@router.post("/logout", summary="登出（吊销当前 token）")
async def logout(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await AuthService(session).logout(principal)
    return success(message="已登出")
