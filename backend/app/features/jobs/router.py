"""异步任务统一查询。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import success
from app.core.security.deps import Principal, get_current_principal
from app.features.datasets.service import DatasetService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", summary="任务状态与进度")
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    data = await DatasetService(session).get_job(job_id, principal.user_id)
    return success(data)
