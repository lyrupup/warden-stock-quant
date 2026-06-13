"""M5 绩效报告 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import success
from app.core.security.deps import Principal, require_user_session
from app.features.reports.schema import CompareBacktestsRequest
from app.features.reports.service import ReportService

router = APIRouter(tags=["Reports"])


@router.get("/backtests/{id}/analysis", summary="扩展绩效分析（月度收益/回撤/归因等）")
async def get_backtest_analysis(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await ReportService(session).get_analysis(principal.user_id, id)
    return success(data.model_dump(by_alias=True))


@router.get("/backtests/{id}/report", summary="绩效报告（HTML 导出）")
async def get_backtest_report(
    id: int,
    format: str = Query("html", enum=["html", "json"]),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
):
    svc = ReportService(session)
    if format == "json":
        data = await svc.get_report(principal.user_id, id)
        return success(data.model_dump())
    html = await svc.render_html(principal.user_id, id)
    filename = f"backtest-report-{id}.html"
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/reports/compare", summary="多回测绩效对比")
async def compare_backtests(
    payload: CompareBacktestsRequest,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await ReportService(session).compare(principal.user_id, payload)
    return success(data.model_dump())
