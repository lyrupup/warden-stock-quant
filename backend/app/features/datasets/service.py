"""M2 数据集业务编排。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.data.client import WardenDataClient
from app.core.data.feed.pg_feed import PgDataFeed
from app.core.errors import ForbiddenError, NotFoundError, ValidationFailedError
from app.core.security.encryption import decrypt_secret, encrypt_secret
from app.features.datasets.models import DataSourceCredential, DataSyncJob, SystemJob
from app.features.datasets.repository import (
    DataSourceRepository,
    DataSyncRepository,
    MarketDataRepository,
    SystemJobRepository,
)
from app.features.datasets.schema import DataSourceCreate, DataSourceView, SyncRequest


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._feed = PgDataFeed(session)
        self._sync_repo = DataSyncRepository(session)
        self._job_repo = SystemJobRepository(session)

    async def get_status(self) -> dict:
        return await self._feed.dataset_status()

    async def trigger_sync(self, user_id: int, payload: SyncRequest) -> tuple[int, str]:
        job = DataSyncJob(
            type=payload.type,
            scope={
                "codes": payload.codes,
                "date_from": payload.date_from.isoformat() if payload.date_from else None,
            },
            status="queued",
        )
        job = await self._sync_repo.create(job)

        from app.tasks.data_tasks import run_data_sync

        async_result = run_data_sync.delay(job.id)
        celery_id = async_result.id
        job.celery_job_id = celery_id
        await self._sync_repo.update_progress(job.id, status="queued")

        sys_job = SystemJob(
            id=celery_id,
            user_id=user_id,
            type="data_sync",
            ref_id=job.id,
            status="queued",
            payload={"sync_type": payload.type},
        )
        await self._job_repo.create(sys_job)
        return job.id, celery_id

    async def get_job(self, job_id: str, user_id: int) -> dict:
        job = await self._job_repo.get(job_id)
        if job is None:
            raise NotFoundError("任务不存在")
        if job.user_id is not None and job.user_id != user_id:
            raise ForbiddenError("越权访问任务")
        return {
            "id": job.id,
            "type": job.type,
            "ref_id": job.ref_id,
            "status": job.status,
            "progress": str(job.progress),
            "result": job.result,
            "error": job.error,
        }


class MarketService:
    def __init__(self, session: AsyncSession) -> None:
        self._feed = PgDataFeed(session)

    async def list_securities(self, kw: Optional[str] = None) -> list[dict]:
        return await self._feed.list_securities(kw)

    async def list_calendar(self, date_from: Optional[str], date_to: Optional[str]) -> list[dict]:
        from datetime import date as dt

        start = dt.fromisoformat(date_from) if date_from else dt(2000, 1, 1)
        end = dt.fromisoformat(date_to) if date_to else dt(2099, 12, 31)
        days = await self._feed.trading_calendar(start, end)
        return [{"trade_date": d.isoformat(), "is_open": True} for d in days]

    async def list_bars(
        self,
        code: str,
        date_from: Optional[str],
        date_to: Optional[str],
        adjust: str = "qfq",
    ) -> list[dict]:
        from datetime import date as dt

        start = dt.fromisoformat(date_from) if date_from else dt(2000, 1, 1)
        end = dt.fromisoformat(date_to) if date_to else dt(2099, 12, 31)
        bars = await self._feed.get_bars(code, start, end, adjust=adjust)
        return [
            {
                "date": b.trade_date.isoformat(),
                "open": str(b.open) if b.open is not None else None,
                "high": str(b.high) if b.high is not None else None,
                "low": str(b.low) if b.low is not None else None,
                "close": str(b.close) if b.close is not None else None,
                "volume": str(b.volume) if b.volume is not None else None,
                "amount": str(b.amount) if b.amount is not None else None,
            }
            for b in bars
        ]


class DataSourceService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DataSourceRepository(session)

    async def list_credentials(self) -> list[DataSourceView]:
        rows = await self._repo.list_all()
        return [
            DataSourceView(
                id=r.id,
                name=r.name,
                base_url=r.base_url,
                secret_id=r.secret_id,
                qps_limit=r.qps_limit,
                daily_quota=r.daily_quota,
                enabled=r.enabled,
            )
            for r in rows
        ]

    async def create_credential(self, payload: DataSourceCreate) -> DataSourceView:
        cred = DataSourceCredential(
            name=payload.name,
            base_url=payload.base_url.rstrip("/"),
            secret_id=payload.secret_id,
            secret_key_enc=encrypt_secret(payload.secret_key),
            qps_limit=payload.qps_limit,
            daily_quota=payload.daily_quota,
            enabled=True,
        )
        cred = await self._repo.create(cred)
        return DataSourceView(
            id=cred.id,
            name=cred.name,
            base_url=cred.base_url,
            secret_id=cred.secret_id,
            qps_limit=cred.qps_limit,
            daily_quota=cred.daily_quota,
            enabled=cred.enabled,
        )



async def build_warden_client_async(session: AsyncSession) -> WardenDataClient:
    settings = get_settings()
    repo = DataSourceRepository(session)
    cred = await repo.get_first_enabled()
    if cred:
        return WardenDataClient(
            cred.base_url,
            cred.secret_id,
            decrypt_secret(cred.secret_key_enc),
        )
    if settings.data_secret_id and settings.data_secret_key:
        return WardenDataClient(
            settings.data_base_url,
            settings.data_secret_id,
            settings.data_secret_key,
        )
    raise ValidationFailedError("未配置数据源凭证，请联系管理员")


async def execute_sync_job(session: AsyncSession, sync_job_id: int) -> dict:
    """执行数据同步（供 Celery worker 调用）。"""
    sync_repo = DataSyncRepository(session)
    market_repo = MarketDataRepository(session)
    job_repo = SystemJobRepository(session)

    job = await sync_repo.get(sync_job_id)
    if job is None:
        raise NotFoundError("同步作业不存在")

    await sync_repo.update_progress(
        sync_job_id,
        status="running",
        progress=Decimal("0"),
    )
    if job.celery_job_id:
        await job_repo.update(job.celery_job_id, status="running", progress=Decimal("0"))

    client = await build_warden_client_async(session)
    try:
        if job.type == "securities":
            data = client.securities()
            total = await market_repo.upsert_securities(data)
            await sync_repo.update_progress(
                sync_job_id,
                status="succeeded",
                progress=Decimal("100"),
                done=total,
                total=total,
                finished_at=datetime.now(timezone.utc),
            )
            result = {"synced": total}
        elif job.type == "daily_bars":
            codes = (job.scope or {}).get("codes") or []
            if not codes:
                secs = client.securities()
                codes = [
                    s.get("stock_code") or s.get("code")
                    for s in secs
                    if s.get("stock_code") or s.get("code")
                ]
            date_from = (job.scope or {}).get("date_from")
            total_bars = 0
            for i, code in enumerate(codes):
                bars = client.kline(code, adjust="", date_from=date_from)
                total_bars += await market_repo.upsert_daily_bars(code, bars)
                pct = Decimal(str(round((i + 1) / max(len(codes), 1) * 100, 2)))
                await sync_repo.update_progress(
                    sync_job_id,
                    progress=pct,
                    done=i + 1,
                    total=len(codes),
                )
                if job.celery_job_id:
                    await job_repo.update(job.celery_job_id, progress=pct)
            await sync_repo.update_progress(
                sync_job_id,
                status="succeeded",
                progress=Decimal("100"),
                finished_at=datetime.now(timezone.utc),
                detail={"bars": total_bars},
            )
            result = {"codes": len(codes), "bars": total_bars}
        else:
            raise ValidationFailedError(f"暂不支持同步类型: {job.type}")
    except Exception as exc:
        await sync_repo.update_progress(
            sync_job_id,
            status="failed",
            error=str(exc),
            finished_at=datetime.now(timezone.utc),
        )
        if job.celery_job_id:
            await job_repo.update(
                job.celery_job_id,
                status="failed",
                error=str(exc),
            )
        raise
    finally:
        client.close()

    if job.celery_job_id:
        await job_repo.update(
            job.celery_job_id,
            status="succeeded",
            progress=Decimal("100"),
            result=result,
        )
    return result
