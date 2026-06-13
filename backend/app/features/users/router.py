"""用户与 API Key 路由（/me、/api-keys）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import success
from app.core.security.deps import (
    Principal,
    get_current_principal,
    require_user_session,
)
from app.features.users.schema import ApiKeyCreate
from app.features.users.service import UserService

me_router = APIRouter(tags=["Auth"])
api_keys_router = APIRouter(prefix="/api-keys", tags=["ApiKeys"])


@me_router.get("/me", summary="当前用户信息与配额")
async def get_me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict:
    data = await UserService(session).get_me(principal.user_id)
    return success(data.model_dump())


@api_keys_router.get("", summary="API Key 列表")
async def list_api_keys(
    principal: Principal = Depends(require_user_session),
    session: AsyncSession = Depends(get_session),
) -> dict:
    items = await UserService(session).list_api_keys(principal.user_id)
    return success([i.model_dump() for i in items])


@api_keys_router.post("", summary="创建 API Key（明文仅此一次返回）")
async def create_api_key(
    payload: ApiKeyCreate,
    principal: Principal = Depends(require_user_session),
    session: AsyncSession = Depends(get_session),
) -> dict:
    created = await UserService(session).create_api_key(principal.user_id, payload)
    return success(created.model_dump(), message="创建成功，请妥善保存明文 key")


@api_keys_router.delete("/{key_id}", summary="吊销 API Key")
async def revoke_api_key(
    key_id: int = Path(..., description="API Key id"),
    principal: Principal = Depends(require_user_session),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await UserService(session).revoke_api_key(principal.user_id, key_id)
    return success(message="已吊销")
