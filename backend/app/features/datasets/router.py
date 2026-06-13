"""M2 数据集与行情只读 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import job_accepted, success
from app.core.security.deps import Principal, get_current_principal, require_role
from app.features.datasets.schema import SyncRequest
from app.features.datasets.service import DatasetService, MarketService

router = APIRouter(tags=["Datasets"])


@router.get("/datasets/status", summary="数据集新鲜度与缺口")
async def dataset_status(
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> dict:
    data = await DatasetService(session).get_status()
    return success(data)


@router.post("/datasets/sync", summary="触发数据同步（异步）")
async def trigger_sync(
    payload: SyncRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    sync_id, celery_id = await DatasetService(session).trigger_sync(principal.user_id, payload)
    return job_accepted(sync_id, celery_id, message="同步任务已入队")


market_router = APIRouter(tags=["Market"])


@market_router.get("/market/securities", summary="证券列表")
async def list_securities(
    kw: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> dict:
    items = await MarketService(session).list_securities(kw)
    return success(items)


@market_router.get("/market/calendar", summary="交易日历")
async def list_calendar(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> dict:
    items = await MarketService(session).list_calendar(date_from, date_to)
    return success(items)


@market_router.get("/market/bars", summary="日K（DataFeed 代理，PIT）")
async def list_bars(
    code: str = Query(...),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    adjust: str = Query("qfq"),
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(get_current_principal),
) -> dict:
    items = await MarketService(session).list_bars(code, date_from, date_to, adjust)
    return success(items)
