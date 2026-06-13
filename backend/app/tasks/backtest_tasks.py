"""M4 回测 Celery 任务。"""

from __future__ import annotations

from app.core.db.session import get_sessionmaker
from app.features.backtests.service import execute_backtest, execute_optimization
from app.tasks.async_runner import run_async
from app.tasks.celery_app import celery_app


@celery_app.task(name="backtest.run", queue="backtest", bind=True)
def run_backtest_task(self, backtest_id: int) -> dict:
    """执行回测作业。"""

    async def _run() -> dict:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            try:
                result = await execute_backtest(session, backtest_id)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    return run_async(_run())


@celery_app.task(name="backtest.optimize", queue="backtest", bind=True)
def run_optimization_task(self, optimization_id: int) -> dict:
    """执行参数寻优作业。"""

    async def _run() -> dict:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            try:
                result = await execute_optimization(session, optimization_id)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    return run_async(_run())
