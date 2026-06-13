"""管理员：数据源凭证等运维接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import success
from app.core.security.deps import Principal, require_role
from app.features.datasets.schema import DataSourceCreate
from app.features.datasets.service import DataSourceService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/data-source", summary="data 服务凭证列表")
async def list_data_sources(
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(require_role("admin")),
) -> dict:
    items = await DataSourceService(session).list_credentials()
    return success([i.model_dump() for i in items])


@router.post("/data-source", summary="配置 data 服务凭证")
async def create_data_source(
    payload: DataSourceCreate,
    session: AsyncSession = Depends(get_session),
    _: Principal = Depends(require_role("admin")),
) -> dict:
    item = await DataSourceService(session).create_credential(payload)
    return success(item.model_dump(), message="数据源凭证已保存")
