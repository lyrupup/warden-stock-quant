"""M4 回测业务编排。"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, QuotaExceededError, ValidationFailedError
from app.core.engine.backtest.compiler import ConfigStrategyCompiler
from app.features.backtests.models import Backtest, BacktestOptimization
from app.features.backtests.repository import BacktestRepository, OptimizationRepository
from app.features.backtests.schema import (
    BacktestCreate,
    BacktestMetricsView,
    BacktestStrategyView,
    BacktestView,
    EquityPointView,
    OptimizationCreate,
    OptimizationResultView,
    OptimizationView,
    PositionView,
    TradeView,
)
from app.features.datasets.models import SystemJob
from app.features.datasets.repository import SystemJobRepository
from app.features.strategies.repository import StrategyRepository

MAX_CONCURRENT_BACKTESTS = 3
MAX_RANGE_DAYS = 3650
MAX_UNIVERSE_CODES = 50
MAX_OPTIM_COMBOS = 200

_CELERY_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes")


class BacktestService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BacktestRepository(session)
        self._strategy_repo = StrategyRepository(session)
        self._job_repo = SystemJobRepository(session)

    def _to_view(
        self, bt: Backtest, meta: Optional[tuple[int, str, int]] = None
    ) -> BacktestView:
        strategy_id, strategy_name, strategy_version = meta or (None, None, None)
        return BacktestView(
            id=bt.id,
            name=bt.name,
            status=bt.status,
            progress=bt.progress,
            job_id=bt.job_id,
            strategy_version_id=bt.strategy_version_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            date_from=bt.date_from,
            date_to=bt.date_to,
            init_capital=bt.init_capital,
            benchmark=bt.benchmark,
            adjust=bt.adjust,
            error=bt.error,
            created_at=bt.created_at,
            finished_at=bt.finished_at,
        )

    def _validate_create(self, payload: BacktestCreate) -> None:
        if payload.date_from > payload.date_to:
            raise ValidationFailedError("date_from 不能晚于 date_to")
        days = (payload.date_to - payload.date_from).days
        if days > MAX_RANGE_DAYS:
            raise ValidationFailedError(f"回测区间不能超过 {MAX_RANGE_DAYS} 天")

    async def create_backtest(self, user_id: int, payload: BacktestCreate) -> tuple[int, str]:
        self._validate_create(payload)
        active = await self._repo.count_active(user_id)
        if active >= MAX_CONCURRENT_BACKTESTS:
            raise QuotaExceededError("并发回测数已达上限，请等待现有任务完成")

        owned = await self._strategy_repo.get_version_owned(
            payload.strategy_version_id, user_id
        )
        if owned is None:
            raise NotFoundError("策略版本不存在")
        strategy, version = owned
        if strategy.type != "config" or not version.config:
            raise ValidationFailedError("仅支持配置式策略回测")
        compiler = ConfigStrategyCompiler(version.config, payload.params)
        if not compiler.supported():
            raise ValidationFailedError(f"暂不支持的信号类型: {compiler.signal_type}")

        universe = (
            payload.universe.model_dump()
            if payload.universe
            else (version.universe or {"type": "list", "codes": []})
        )

        bt = Backtest(
            user_id=user_id,
            strategy_version_id=version.id,
            name=payload.name or f"{strategy.name} 回测",
            params=payload.params,
            universe=universe,
            date_from=payload.date_from,
            date_to=payload.date_to,
            init_capital=payload.init_capital,
            benchmark=payload.benchmark,
            cost_config=payload.cost_config,
            adjust=payload.adjust,
            status="queued",
            progress=Decimal("0"),
        )
        await self._repo.add(bt)
        await self._session.flush()

        if _CELERY_EAGER:
            # 测试/本地 eager：同会话直接执行，避免 Celery 嵌套事件循环与 sqlite 死锁。
            celery_id = f"eager-{bt.id}"
            await self._repo.update_status(bt.id, job_id=celery_id)
            await execute_backtest(self._session, bt.id)
        else:
            await self._session.commit()
            from app.tasks.backtest_tasks import run_backtest_task

            async_result = run_backtest_task.delay(bt.id)
            celery_id = async_result.id
            await self._repo.update_status(bt.id, job_id=celery_id)

        sys_job = SystemJob(
            id=celery_id,
            user_id=user_id,
            type="backtest",
            ref_id=bt.id,
            status="queued",
            payload={"backtest_id": bt.id},
        )
        await self._job_repo.create(sys_job)
        return bt.id, celery_id

    async def list_backtests(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[BacktestView], int]:
        rows, total = await self._repo.list_by_user(user_id, page, size)
        metas = await self._strategy_repo.get_version_meta(
            [r.strategy_version_id for r in rows]
        )
        return [self._to_view(r, metas.get(r.strategy_version_id)) for r in rows], total

    async def get_backtest(self, user_id: int, backtest_id: int) -> BacktestView:
        bt = await self._require_owned(backtest_id, user_id)
        metas = await self._strategy_repo.get_version_meta([bt.strategy_version_id])
        return self._to_view(bt, metas.get(bt.strategy_version_id))

    async def get_backtest_strategy(
        self, user_id: int, backtest_id: int
    ) -> BacktestStrategyView:
        bt = await self._require_owned(backtest_id, user_id)
        owned = await self._strategy_repo.get_version_owned(
            bt.strategy_version_id, user_id
        )
        if owned is None:
            # 策略已被删除，仅能回显回测自身保存的股票池/参数
            return BacktestStrategyView(
                strategy_version_id=bt.strategy_version_id,
                universe=bt.universe,
                params=bt.params,
            )
        strategy, version = owned
        return BacktestStrategyView(
            strategy_version_id=version.id,
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            version=version.version,
            type=strategy.type,
            description=strategy.description,
            config=version.config,
            # 股票池以本次回测实际生效的为准（创建时可覆盖策略默认值）
            universe=bt.universe,
            params=bt.params,
            created_at=version.created_at,
        )

    async def cancel_backtest(self, user_id: int, backtest_id: int) -> None:
        bt = await self._require_owned(backtest_id, user_id)
        if bt.status in ("succeeded", "failed", "canceled"):
            return
        await self._repo.update_status(backtest_id, status="canceled")

    async def get_metrics(self, user_id: int, backtest_id: int) -> BacktestMetricsView:
        await self._require_owned(backtest_id, user_id)
        m = await self._repo.get_metrics(backtest_id)
        if m is None:
            raise NotFoundError("回测结果尚未生成")
        return BacktestMetricsView.model_validate(m, from_attributes=True)

    async def get_equity(self, user_id: int, backtest_id: int) -> list[EquityPointView]:
        await self._require_owned(backtest_id, user_id)
        rows = await self._repo.list_equity(backtest_id)
        return [EquityPointView.model_validate(r, from_attributes=True) for r in rows]

    async def list_trades(
        self, user_id: int, backtest_id: int, page: int, size: int
    ) -> tuple[list[TradeView], int]:
        await self._require_owned(backtest_id, user_id)
        rows, total = await self._repo.list_trades(backtest_id, page, size)
        return [TradeView.model_validate(r, from_attributes=True) for r in rows], total

    async def list_positions(
        self, user_id: int, backtest_id: int, trade_date: Optional[Any] = None
    ) -> list[PositionView]:
        await self._require_owned(backtest_id, user_id)
        rows = await self._repo.list_positions(backtest_id, trade_date)
        return [PositionView.model_validate(r, from_attributes=True) for r in rows]

    async def _require_owned(self, backtest_id: int, user_id: int) -> Backtest:
        bt = await self._repo.get_owned(backtest_id, user_id)
        if bt is None:
            raise NotFoundError("回测不存在")
        return bt


async def execute_backtest(session: AsyncSession, backtest_id: int) -> dict:
    """Worker 内执行回测并落库。"""
    repo = BacktestRepository(session)
    strategy_repo = StrategyRepository(session)
    job_repo = SystemJobRepository(session)

    bt = (
        await session.execute(select(Backtest).where(Backtest.id == backtest_id))
    ).scalar_one_or_none()
    if bt is None:
        raise NotFoundError("回测不存在")
    if bt.status == "canceled":
        return {"status": "canceled"}

    version_pair = await strategy_repo.get_version_owned(bt.strategy_version_id, bt.user_id)
    if version_pair is None:
        raise NotFoundError("策略版本不存在")
    _strategy, version = version_pair

    await repo.update_status(backtest_id, status="running", progress=Decimal("1"))
    if bt.job_id:
        await job_repo.update(bt.job_id, status="running", progress=Decimal("1"))

    from app.core.engine.backtest.data_loader import build_engine_input
    from app.core.engine.backtest.simulator import BacktestCanceledError, run_backtest

    async def _is_canceled() -> bool:
        row = await repo.get_owned(backtest_id, bt.user_id)
        return row is not None and row.status == "canceled"

    try:
        engine_in = await build_engine_input(
            session,
            date_from=bt.date_from,
            date_to=bt.date_to,
            init_capital=float(bt.init_capital),
            adjust=bt.adjust,
            cost_config=bt.cost_config,
            strategy_config=version.config or {},
            universe=bt.universe,
            params=bt.params,
            benchmark=bt.benchmark,
            max_codes=MAX_UNIVERSE_CODES,
            user_id=bt.user_id,
        )

        cancel_flag = {"v": False}

        def should_cancel() -> bool:
            return cancel_flag["v"]

        async def refresh_cancel() -> None:
            cancel_flag["v"] = await _is_canceled()

        def on_progress(p: float) -> None:
            # 同步回调内不 await；进度在关键节点由外层刷新
            pass

        await refresh_cancel()
        if cancel_flag["v"]:
            raise BacktestCanceledError("回测已取消")

        output = run_backtest(engine_in, on_progress=on_progress, should_cancel=should_cancel)

        equity_rows = [
            {
                "trade_date": p.trade_date,
                "nav": Decimal(str(round(p.nav, 8))),
                "benchmark_nav": Decimal(str(round(p.benchmark_nav, 8)))
                if p.benchmark_nav is not None
                else None,
                "drawdown": Decimal(str(round(p.drawdown, 8))),
                "cash": Decimal(str(round(p.cash, 4))),
                "market_value": Decimal(str(round(p.market_value, 4))),
            }
            for p in output.equity
        ]
        trade_rows = [
            {
                "trade_date": t.trade_date,
                "code": t.code,
                "side": t.side,
                "price": Decimal(str(round(t.price, 4))),
                "qty": t.qty,
                "amount": Decimal(str(round(t.amount, 4))),
                "commission": Decimal(str(round(t.commission, 4))),
                "tax": Decimal(str(round(t.tax, 4))),
                "pnl": Decimal(str(round(t.pnl, 4))) if t.pnl is not None else None,
            }
            for t in output.trades
        ]
        pos_rows = [
            {
                "trade_date": p.trade_date,
                "code": p.code,
                "qty": p.qty,
                "price": Decimal(str(round(p.price, 4))),
                "market_value": Decimal(str(round(p.market_value, 4))),
                "weight": Decimal(str(round(p.weight, 8))),
            }
            for p in output.positions
        ]
        metrics = {
            k: Decimal(str(v)) if isinstance(v, (int, float)) and v is not None else v
            for k, v in output.metrics.items()
        }

        await repo.save_results(backtest_id, metrics, equity_rows, trade_rows, pos_rows)
        finished = datetime.now(timezone.utc)
        await repo.update_status(
            backtest_id,
            status="succeeded",
            progress=Decimal("100"),
            finished_at=finished,
        )
        if bt.job_id:
            await job_repo.update(
                bt.job_id, status="succeeded", progress=Decimal("100")
            )
        return {"status": "succeeded", "backtest_id": backtest_id}

    except BacktestCanceledError:
        finished = datetime.now(timezone.utc)
        await repo.update_status(
            backtest_id, status="canceled", progress=Decimal("0"), finished_at=finished
        )
        if bt.job_id:
            await job_repo.update(bt.job_id, status="canceled")
        return {"status": "canceled"}
    except Exception as exc:
        finished = datetime.now(timezone.utc)
        await repo.update_status(
            backtest_id,
            status="failed",
            error=str(exc),
            finished_at=finished,
        )
        if bt.job_id:
            await job_repo.update(bt.job_id, status="failed", error=str(exc))
        raise


MAX_CONCURRENT_OPTIM = 1


class OptimizationService:
    """参数寻优业务编排。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OptimizationRepository(session)
        self._strategy_repo = StrategyRepository(session)
        self._job_repo = SystemJobRepository(session)

    def _to_view(
        self, opt: BacktestOptimization, meta: Optional[tuple[int, str, int]] = None
    ) -> OptimizationView:
        strategy_id, strategy_name, strategy_version = meta or (None, None, None)
        return OptimizationView(
            id=opt.id,
            name=opt.name,
            status=opt.status,
            progress=opt.progress,
            job_id=opt.job_id,
            strategy_version_id=opt.strategy_version_id,
            strategy_name=strategy_name,
            strategy_version=strategy_version,
            method=opt.method,
            objective=opt.objective,
            oos_split=opt.oos_split,
            total_combos=opt.total_combos,
            param_space=opt.param_space,
            date_from=opt.date_from,
            date_to=opt.date_to,
            init_capital=opt.init_capital,
            benchmark=opt.benchmark,
            adjust=opt.adjust,
            summary=opt.summary,
            error=opt.error,
            created_at=opt.created_at,
            finished_at=opt.finished_at,
        )

    async def create_optimization(
        self, user_id: int, payload: OptimizationCreate
    ) -> tuple[int, str]:
        from app.core.engine.backtest.optimizer import generate_combos

        if payload.date_from > payload.date_to:
            raise ValidationFailedError("date_from 不能晚于 date_to")
        active = await self._repo.count_active(user_id)
        if active >= MAX_CONCURRENT_OPTIM:
            raise QuotaExceededError("已有寻优任务在运行，请等待完成")

        owned = await self._strategy_repo.get_version_owned(
            payload.strategy_version_id, user_id
        )
        if owned is None:
            raise NotFoundError("策略版本不存在")
        strategy, version = owned
        if strategy.type != "config" or not version.config:
            raise ValidationFailedError("仅支持配置式策略寻优")
        compiler = ConfigStrategyCompiler(version.config, {})
        if not compiler.supported():
            raise ValidationFailedError(f"暂不支持的信号类型: {compiler.signal_type}")

        combos = generate_combos(payload.param_space, payload.method, payload.n_iter)
        if not combos:
            raise ValidationFailedError("参数空间为空")
        if len(combos) > MAX_OPTIM_COMBOS:
            raise ValidationFailedError(
                f"参数组合数 {len(combos)} 超过上限 {MAX_OPTIM_COMBOS}，请缩小空间或改用随机搜索"
            )

        universe = (
            payload.universe.model_dump()
            if payload.universe
            else (version.universe or {"type": "list", "codes": []})
        )
        opt = BacktestOptimization(
            user_id=user_id,
            strategy_version_id=version.id,
            name=payload.name or f"{strategy.name} 寻优",
            param_space=payload.param_space,
            method=payload.method,
            objective=payload.objective,
            oos_split=Decimal(str(payload.oos_split)),
            universe=universe,
            date_from=payload.date_from,
            date_to=payload.date_to,
            init_capital=payload.init_capital,
            benchmark=payload.benchmark,
            cost_config=payload.cost_config,
            adjust=payload.adjust,
            total_combos=len(combos),
            status="queued",
            progress=Decimal("0"),
        )
        await self._repo.add(opt)
        await self._session.flush()

        if _CELERY_EAGER:
            celery_id = f"eager-opt-{opt.id}"
            await self._repo.update_status(opt.id, job_id=celery_id)
            await execute_optimization(self._session, opt.id)
        else:
            await self._session.commit()
            from app.tasks.backtest_tasks import run_optimization_task

            async_result = run_optimization_task.delay(opt.id)
            celery_id = async_result.id
            await self._repo.update_status(opt.id, job_id=celery_id)

        sys_job = SystemJob(
            id=celery_id,
            user_id=user_id,
            type="optimization",
            ref_id=opt.id,
            status="queued",
            payload={"optimization_id": opt.id},
        )
        await self._job_repo.create(sys_job)
        return opt.id, celery_id

    async def list_optimizations(
        self, user_id: int, page: int, size: int
    ) -> tuple[list[OptimizationView], int]:
        rows, total = await self._repo.list_by_user(user_id, page, size)
        metas = await self._strategy_repo.get_version_meta(
            [r.strategy_version_id for r in rows]
        )
        return [self._to_view(r, metas.get(r.strategy_version_id)) for r in rows], total

    async def get_optimization(
        self, user_id: int, optimization_id: int
    ) -> OptimizationView:
        opt = await self._require_owned(optimization_id, user_id)
        metas = await self._strategy_repo.get_version_meta([opt.strategy_version_id])
        return self._to_view(opt, metas.get(opt.strategy_version_id))

    async def list_results(
        self, user_id: int, optimization_id: int
    ) -> list[OptimizationResultView]:
        await self._require_owned(optimization_id, user_id)
        rows = await self._repo.list_results(optimization_id)
        return [
            OptimizationResultView.model_validate(r, from_attributes=True) for r in rows
        ]

    async def cancel_optimization(self, user_id: int, optimization_id: int) -> None:
        opt = await self._require_owned(optimization_id, user_id)
        if opt.status in ("succeeded", "failed", "canceled"):
            return
        await self._repo.update_status(optimization_id, status="canceled")

    async def _require_owned(
        self, optimization_id: int, user_id: int
    ) -> BacktestOptimization:
        opt = await self._repo.get_owned(optimization_id, user_id)
        if opt is None:
            raise NotFoundError("寻优任务不存在")
        return opt


def _jsonify_metrics(metrics: Optional[dict]) -> Optional[dict]:
    """将指标里的非 JSON 安全类型（date/Decimal）转为可存 JSON 的形式。"""
    if not metrics:
        return metrics
    out: dict[str, Any] = {}
    for k, v in metrics.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


async def execute_optimization(session: AsyncSession, optimization_id: int) -> dict:
    """Worker 内执行参数寻优并落库。"""
    from app.core.engine.backtest.data_loader import build_engine_input
    from app.core.engine.backtest.optimizer import generate_combos, run_optimization

    repo = OptimizationRepository(session)
    strategy_repo = StrategyRepository(session)
    job_repo = SystemJobRepository(session)

    opt = (
        await session.execute(
            select(BacktestOptimization).where(
                BacktestOptimization.id == optimization_id
            )
        )
    ).scalar_one_or_none()
    if opt is None:
        raise NotFoundError("寻优任务不存在")
    if opt.status == "canceled":
        return {"status": "canceled"}

    version_pair = await strategy_repo.get_version_owned(
        opt.strategy_version_id, opt.user_id
    )
    if version_pair is None:
        raise NotFoundError("策略版本不存在")
    _strategy, version = version_pair

    await repo.update_status(optimization_id, status="running", progress=Decimal("1"))
    if opt.job_id:
        await job_repo.update(opt.job_id, status="running", progress=Decimal("1"))

    try:
        base = await build_engine_input(
            session,
            date_from=opt.date_from,
            date_to=opt.date_to,
            init_capital=float(opt.init_capital),
            adjust=opt.adjust,
            cost_config=opt.cost_config,
            strategy_config=version.config or {},
            universe=opt.universe,
            params={},
            benchmark=opt.benchmark,
            max_codes=MAX_UNIVERSE_CODES,
        )
        combos = generate_combos(opt.param_space, opt.method, opt.total_combos)
        outcome = run_optimization(
            base,
            combos,
            objective=opt.objective,
            oos_split=float(opt.oos_split),
        )

        rows = [
            {
                "params": r["params"],
                "objective_value": (
                    Decimal(str(r["objective_value"]))
                    if r["objective_value"] is not None
                    else None
                ),
                "is_metrics": _jsonify_metrics(r["is_metrics"]),
                "oos_metrics": _jsonify_metrics(r["oos_metrics"]),
                "rank": r["rank"],
            }
            for r in outcome["results"]
        ]
        await repo.save_results(optimization_id, rows)
        finished = datetime.now(timezone.utc)
        await repo.update_status(
            optimization_id,
            status="succeeded",
            progress=Decimal("100"),
            summary=outcome["summary"],
            finished_at=finished,
        )
        if opt.job_id:
            await job_repo.update(opt.job_id, status="succeeded", progress=Decimal("100"))
        return {"status": "succeeded", "optimization_id": optimization_id}
    except Exception as exc:
        finished = datetime.now(timezone.utc)
        await repo.update_status(
            optimization_id, status="failed", error=str(exc), finished_at=finished
        )
        if opt.job_id:
            await job_repo.update(opt.job_id, status="failed", error=str(exc))
        raise
