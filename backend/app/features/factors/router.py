"""M6 因子 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import job_accepted, paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.factors.schema import (
    FactorAnalyzeRequest,
    FactorCombineRequest,
    FactorComputeRequest,
    FactorUpsert,
)
from app.features.factors.service import FactorService

router = APIRouter(tags=["Factors"])


@router.get("/factors", summary="因子列表")
async def list_factors(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await FactorService(session).list_factors(principal.user_id, page, size)
    return paginated(items, total, page, size)


@router.post("/factors", summary="创建因子")
async def create_factor(
    payload: FactorUpsert,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await FactorService(session).create_factor(principal.user_id, payload)
    return success(data, message="创建成功")


@router.get("/factors/{id}", summary="因子详情")
async def get_factor(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await FactorService(session).get_factor(principal.user_id, id)
    return success(data)


@router.delete("/factors/{id}", summary="删除因子")
async def delete_factor(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    await FactorService(session).delete_factor(principal.user_id, id)
    return success(message="已删除")


@router.post("/factors/{id}/compute", summary="计算因子值（异步）")
async def compute_factor(
    id: int,
    payload: FactorComputeRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    ref_id, job_id = await FactorService(session).trigger_compute(
        principal.user_id, id, payload
    )
    return job_accepted(ref_id, job_id)


@router.post("/factors/{id}/analyze", summary="因子检验 IC/分层（异步）")
async def analyze_factor(
    id: int,
    payload: FactorAnalyzeRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    analysis_id, job_id = await FactorService(session).trigger_analyze(
        principal.user_id, id, payload
    )
    return job_accepted(analysis_id, job_id)


@router.get("/factors/{id}/analyses/{aid}", summary="因子分析结果")
async def get_factor_analysis(
    id: int,
    aid: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await FactorService(session).get_analysis(principal.user_id, id, aid)
    return success(data)


@router.post("/factors/combine", summary="多因子合成")
async def combine_factors(
    payload: FactorCombineRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await FactorService(session).combine(principal.user_id, payload)
    return success(data, message="合成因子已创建")
