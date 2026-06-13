"""M2 数据同步 Celery 任务。"""

from __future__ import annotations

import asyncio

from app.core.db.session import get_sessionmaker
from app.features.datasets.service import execute_sync_job
from app.tasks.celery_app import celery_app


@celery_app.task(name="data.run_sync", queue="data", bind=True)
def run_data_sync(self, sync_job_id: int) -> dict:
    """执行数据同步作业。"""

    async def _run() -> dict:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            try:
                result = await execute_sync_job(session, sync_job_id)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    return asyncio.run(_run())
