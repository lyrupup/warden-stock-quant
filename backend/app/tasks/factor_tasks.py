"""M6 因子 Celery 任务。"""

from __future__ import annotations

from decimal import Decimal

from app.core.db.session import get_sessionmaker
from app.features.datasets.repository import SystemJobRepository
from app.features.factors.service import execute_factor_analyze, execute_factor_compute
from app.tasks.async_runner import run_async
from app.tasks.celery_app import celery_app


@celery_app.task(name="factor.compute", queue="factor", bind=True)
def run_factor_compute(self, factor_id: int, user_id: int, payload: dict) -> dict:
    async def _run() -> dict:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            job_repo = SystemJobRepository(session)
            try:
                if self.request.id:
                    await job_repo.update(self.request.id, status="running", progress=Decimal("10"))
                result = await execute_factor_compute(session, factor_id, user_id, payload)
                if self.request.id:
                    await job_repo.update(self.request.id, status="succeeded", progress=Decimal("100"))
                await session.commit()
                return result
            except Exception as exc:
                if self.request.id:
                    await job_repo.update(self.request.id, status="failed", error=str(exc))
                await session.commit()
                raise

    return run_async(_run())


@celery_app.task(name="factor.analyze", queue="factor", bind=True)
def run_factor_analyze(self, analysis_id: int, user_id: int, payload: dict) -> dict:
    async def _run() -> dict:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            job_repo = SystemJobRepository(session)
            try:
                if self.request.id:
                    await job_repo.update(self.request.id, status="running", progress=Decimal("10"))
                result = await execute_factor_analyze(session, analysis_id, user_id, payload)
                await session.commit()
                return result
            except Exception as exc:
                if self.request.id:
                    await job_repo.update(self.request.id, status="failed", error=str(exc))
                await session.commit()
                raise

    return run_async(_run())
