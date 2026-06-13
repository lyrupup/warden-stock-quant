"""M6 因子业务编排。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine.backtest.data_loader import bar_row_to_data, resolve_universe_codes
from app.core.engine.factor.analysis import run_factor_analysis
from app.core.engine.factor.compute import (
    BUILTIN_FACTORS,
    compute_factor_matrix,
    list_builtin_factors,
)
from app.core.data.feed.pg_feed import PgDataFeed
from app.core.errors import ConflictError, NotFoundError, ValidationFailedError
from app.features.datasets.models import SystemJob
from app.features.datasets.repository import SystemJobRepository
from app.features.factors.models import Factor, FactorAnalysis
from app.features.factors.repository import FactorRepository
from app.features.factors.schema import (
    FactorAnalyzeRequest,
    FactorCombineRequest,
    FactorComputeRequest,
    FactorUpsert,
    FactorView,
)


class FactorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = FactorRepository(session)
        self._job_repo = SystemJobRepository(session)

    def _to_view(self, factor: Factor) -> dict:
        return FactorView(
            id=factor.id,
            name=factor.name,
            category=factor.category,
            type=factor.type,
            expr=factor.expr,
            code=factor.code,
            params=factor.params,
            direction=factor.direction,
            created_at=factor.created_at,
        ).model_dump()

    async def list_factors(self, user_id: int, page: int, size: int) -> tuple[list[dict], int]:
        rows, total = await self._repo.list_by_user(user_id, page, size)
        builtins = list_builtin_factors()
        items = [self._to_view(r) for r in rows]
        if page == 1:
            items = builtins + items
            total += len(builtins)
        return items, total

    async def get_factor(self, user_id: int, factor_id: int) -> dict:
        factor = await self._require_owned(factor_id, user_id)
        return self._to_view(factor)

    async def create_factor(self, user_id: int, payload: FactorUpsert) -> dict:
        if payload.name in BUILTIN_FACTORS:
            raise ConflictError("内置因子名称不可占用")
        existing = await self._repo.get_by_name(user_id, payload.name)
        if existing:
            raise ConflictError("同名因子已存在")
        if payload.type == "code":
            raise ValidationFailedError("代码式因子暂未开放")
        factor = Factor(
            user_id=user_id,
            name=payload.name,
            category=payload.category,
            type=payload.type,
            expr=payload.expr,
            code=payload.code,
            params=payload.params,
            direction=payload.direction,
        )
        await self._repo.add(factor)
        return self._to_view(factor)

    async def delete_factor(self, user_id: int, factor_id: int) -> None:
        factor = await self._require_owned(factor_id, user_id)
        await self._repo.delete(factor)

    async def trigger_compute(
        self, user_id: int, factor_id: int, payload: FactorComputeRequest
    ) -> tuple[int, str]:
        factor = await self._require_owned(factor_id, user_id)
        from app.tasks.factor_tasks import run_factor_compute

        async_result = run_factor_compute.delay(
            factor.id,
            user_id,
            payload.model_dump(mode="json"),
        )
        job_id = async_result.id
        sys_job = SystemJob(
            id=job_id,
            user_id=user_id,
            type="factor_compute",
            ref_id=factor.id,
            status="queued",
            payload={"factor_id": factor.id},
        )
        await self._job_repo.create(sys_job)
        return factor.id, job_id

    async def trigger_analyze(
        self, user_id: int, factor_id: int, payload: FactorAnalyzeRequest
    ) -> tuple[int, str]:
        factor = await self._require_owned(factor_id, user_id)
        analysis = FactorAnalysis(
            factor_id=factor.id,
            universe=payload.universe,
            date_from=payload.date_from,
            date_to=payload.date_to,
            forward_period=payload.forward_period,
            n_quantiles=payload.n_quantiles,
            status="queued",
        )
        await self._repo.add_analysis(analysis)

        from app.tasks.factor_tasks import run_factor_analyze

        async_result = run_factor_analyze.delay(analysis.id, user_id, payload.model_dump(mode="json"))
        job_id = async_result.id
        analysis.job_id = job_id
        analysis.status = "queued"
        await self._session.flush()

        sys_job = SystemJob(
            id=job_id,
            user_id=user_id,
            type="factor_analyze",
            ref_id=analysis.id,
            status="queued",
            payload={"factor_id": factor.id, "analysis_id": analysis.id},
        )
        await self._job_repo.create(sys_job)
        return analysis.id, job_id

    async def get_analysis(self, user_id: int, factor_id: int, analysis_id: int) -> dict:
        await self._require_owned(factor_id, user_id)
        row = await self._repo.get_analysis(factor_id, analysis_id)
        if row is None:
            raise NotFoundError("因子分析不存在")
        return {
            "id": row.id,
            "status": row.status,
            "forward_period": row.forward_period,
            "n_quantiles": row.n_quantiles,
            "ic_mean": row.ic_mean,
            "ic_ir": row.ic_ir,
            "ic_win_rate": row.ic_win_rate,
            "ic_series": row.ic_series,
            "quantile_returns": row.quantile_returns,
            "turnover": row.turnover,
            "job_id": row.job_id,
            "created_at": row.created_at,
        }

    async def combine(self, user_id: int, payload: FactorCombineRequest) -> dict:
        if payload.neutralize:
            raise ValidationFailedError("行业/市值中性化待上游接口，暂不支持")
        weights: list[float] = []
        members_meta: list[dict] = []
        for m in payload.members:
            fid = int(m["factor_id"])
            factor = await self._require_owned(fid, user_id)
            w = float(m.get("weight", 1.0))
            weights.append(w)
            members_meta.append({"factor_id": fid, "name": factor.name, "weight": w})
        if not weights:
            raise ValidationFailedError("members 不能为空")
        if payload.scheme == "equal":
            weights = [1.0 / len(weights)] * len(weights)
        else:
            total = sum(weights) or 1.0
            weights = [w / total for w in weights]
        composite = Factor(
            user_id=user_id,
            name=payload.name,
            category="composite",
            type="expr",
            expr=f"combine:{payload.scheme}",
            params={"members": members_meta, "weights": weights},
            direction=1,
        )
        existing = await self._repo.get_by_name(user_id, payload.name)
        if existing:
            raise ConflictError("同名因子已存在")
        await self._repo.add(composite)
        return self._to_view(composite)

    async def _require_owned(self, factor_id: int, user_id: int) -> Factor:
        factor = await self._repo.get_owned(factor_id, user_id)
        if factor is None:
            raise NotFoundError("因子不存在")
        return factor


async def execute_factor_compute(
    session: AsyncSession,
    factor_id: int,
    user_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    repo = FactorRepository(session)
    job_repo = SystemJobRepository(session)
    factor = await repo.get_owned(factor_id, user_id)
    if factor is None:
        raise NotFoundError("因子不存在")

    req = FactorComputeRequest.model_validate(payload)
    feed = PgDataFeed(session)
    status = await feed.dataset_status()
    latest_str = status.get("bars_updated_to") or status.get("latest_trade_date")
    date_to = req.date_to or (date.fromisoformat(latest_str) if latest_str else date.today())
    date_from = req.date_from or (date_to - timedelta(days=365))
    warmup = date_from - timedelta(days=120)
    calendar = await feed.trading_calendar(warmup, date_to)
    codes = await resolve_universe_codes(session, req.universe, max_codes=100)
    if not codes:
        raise ValidationFailedError("股票池为空")

    bars_by_code = {}
    for code in codes:
        rows = await feed.get_bars(code, warmup, date_to, adjust="qfq")
        if rows:
            bars_by_code[code] = bar_row_to_data(code, rows)
    if not bars_by_code:
        raise ValidationFailedError("无可用行情数据")

    factor_name = factor.expr or factor.name
    if factor.type == "builtin" or factor.name in BUILTIN_FACTORS:
        factor_name = factor.name

    matrix = compute_factor_matrix(
        bars_by_code,
        calendar,
        factor_name,
        factor.params,
        factor.direction,
    )
    cal_index = {d: i for i, d in enumerate(calendar)}
    value_rows: list[tuple[str, date, Decimal]] = []
    for code, arr in matrix.items():
        for d in calendar:
            if d < date_from or d > date_to:
                continue
            v = arr[cal_index[d]]
            if v != v:  # NaN
                continue
            value_rows.append((code, d, Decimal(str(round(float(v), 8)))))

    await repo.save_values(factor_id, value_rows)
    return {"factor_id": factor_id, "rows": len(value_rows)}


async def execute_factor_analyze(
    session: AsyncSession,
    analysis_id: int,
    user_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    repo = FactorRepository(session)
    job_repo = SystemJobRepository(session)
    analysis = await session.get(FactorAnalysis, analysis_id)
    if analysis is None:
        raise NotFoundError("分析任务不存在")
    factor = await repo.get_owned(analysis.factor_id, user_id)
    if factor is None:
        raise NotFoundError("因子不存在")

    req = FactorAnalyzeRequest.model_validate(payload)
    await repo.update_analysis(analysis_id, status="running")

    feed = PgDataFeed(session)
    status = await feed.dataset_status()
    latest_str = status.get("bars_updated_to") or status.get("latest_trade_date")
    default_to = date.fromisoformat(latest_str) if latest_str else date.today()
    date_to = req.date_to or analysis.date_to or default_to
    date_from = req.date_from or analysis.date_from or (date_to - timedelta(days=365))
    warmup = date_from - timedelta(days=120)
    calendar = await feed.trading_calendar(warmup, date_to)
    universe = req.universe or analysis.universe
    codes = await resolve_universe_codes(session, universe, max_codes=100)

    bars_by_code = {}
    for code in codes:
        rows = await feed.get_bars(code, warmup, date_to, adjust="qfq")
        if rows:
            bars_by_code[code] = bar_row_to_data(code, rows)

    factor_name = factor.expr or factor.name
    if factor.type == "builtin" or factor.name in BUILTIN_FACTORS:
        factor_name = factor.name

    result = run_factor_analysis(
        bars_by_code=bars_by_code,
        calendar=calendar,
        factor_name=factor_name,
        factor_params=factor.params,
        direction=factor.direction,
        forward_period=req.forward_period,
        n_quantiles=req.n_quantiles,
        date_from=date_from,
        date_to=date_to,
    )

    await repo.update_analysis(
        analysis_id,
        status="succeeded",
        ic_mean=Decimal(str(round(result["ic_mean"], 8))),
        ic_ir=Decimal(str(round(result["ic_ir"], 8))),
        ic_win_rate=Decimal(str(round(result["ic_win_rate"], 8))),
        ic_series=result["ic_series"],
        quantile_returns=result["quantile_returns"],
        turnover=result["turnover"],
        date_from=date_from,
        date_to=date_to,
    )
    if analysis.job_id:
        await job_repo.update(analysis.job_id, status="succeeded", progress=Decimal("100"))
    return {"analysis_id": analysis_id, **result}
