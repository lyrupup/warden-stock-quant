"""M10 告警 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.alerts.schema import AlertChannelCreate
from app.features.alerts.service import AlertService

router = APIRouter(tags=["Alerts"])


@router.get("/alerts/channels", summary="告警渠道列表")
async def list_channels(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items = await AlertService(session).list_channels(principal.user_id)
    return success(items)


@router.post("/alerts/channels", summary="创建告警渠道")
async def create_channel(
    payload: AlertChannelCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await AlertService(session).create_channel(principal.user_id, payload)
    return success(data, message="创建成功")


@router.delete("/alerts/channels/{id}", summary="删除告警渠道")
async def delete_channel(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    await AlertService(session).delete_channel(principal.user_id, id)
    return success(message="已删除")


@router.get("/alerts", summary="告警记录")
async def list_alerts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await AlertService(session).list_alerts(principal.user_id, page, size)
    return paginated(items, total, page, size)
