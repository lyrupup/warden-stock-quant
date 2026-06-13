"""异步任务统一查询。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import paginated, success
from app.core.security.deps import Principal, get_current_principal
from app.features.datasets.models import SystemJob
from app.features.datasets.service import DatasetService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", summary="任务列表")
async def list_jobs(
    type: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    stmt = select(SystemJob).where(SystemJob.user_id == principal.user_id)
    if type:
        stmt = stmt.where(SystemJob.type == type)
    stmt = stmt.order_by(SystemJob.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    total = len(rows)
    start = (page - 1) * size
    items = [
        {
            "id": j.id,
            "type": j.type,
            "ref_id": j.ref_id,
            "status": j.status,
            "progress": float(j.progress),
            "error": j.error,
            "created_at": j.created_at,
            "updated_at": j.updated_at,
        }
        for j in rows[start : start + size]
    ]
    return paginated(items, total, page, size)


@router.get("/{job_id}", summary="任务状态与进度")
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_current_principal),
) -> dict:
    data = await DatasetService(session).get_job(job_id, principal.user_id)
    return success(data)
