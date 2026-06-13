"""数据集与同步作业数据访问。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.datasets.models import (
    DataSourceCredential,
    DataSyncJob,
    MarketDailyBar,
    MarketSecurity,
    SystemJob,
)


class DataSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_enabled(self) -> list[DataSourceCredential]:
        rows = (
            await self._session.execute(
                select(DataSourceCredential).where(DataSourceCredential.enabled.is_(True))
            )
        ).scalars().all()
        return list(rows)

    async def get_first_enabled(self) -> Optional[DataSourceCredential]:
        creds = await self.list_enabled()
        return creds[0] if creds else None

    async def create(self, cred: DataSourceCredential) -> DataSourceCredential:
        self._session.add(cred)
        await self._session.flush()
        return cred

    async def list_all(self) -> list[DataSourceCredential]:
        rows = (await self._session.execute(select(DataSourceCredential))).scalars().all()
        return list(rows)


class DataSyncRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job: DataSyncJob) -> DataSyncJob:
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> Optional[DataSyncJob]:
        return await self._session.get(DataSyncJob, job_id)

    async def update_progress(
        self,
        job_id: int,
        *,
        status: Optional[str] = None,
        progress: Optional[Decimal] = None,
        done: Optional[int] = None,
        failed: Optional[int] = None,
        total: Optional[int] = None,
        error: Optional[str] = None,
        detail: Optional[dict] = None,
        finished_at: Optional[datetime] = None,
    ) -> None:
        values: dict = {}
        if status is not None:
            values["status"] = status
        if progress is not None:
            values["progress"] = progress
        if done is not None:
            values["done"] = done
        if failed is not None:
            values["failed"] = failed
        if total is not None:
            values["total"] = total
        if error is not None:
            values["error"] = error
        if detail is not None:
            values["detail"] = detail
        if finished_at is not None:
            values["finished_at"] = finished_at
        if values:
            await self._session.execute(
                update(DataSyncJob).where(DataSyncJob.id == job_id).values(**values)
            )


class MarketDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_securities(self, items: Sequence[dict]) -> int:
        count = 0
        for item in items:
            code = item.get("stock_code") or item.get("code")
            if not code:
                continue
            existing = await self._session.get(MarketSecurity, code)
            if existing:
                existing.name = item.get("stock_name") or item.get("name") or existing.name
                existing.board = item.get("board") or existing.board
                existing.market = item.get("market") or existing.market
            else:
                self._session.add(
                    MarketSecurity(
                        code=code,
                        name=item.get("stock_name") or item.get("name"),
                        market=item.get("market") or "CN",
                        board=item.get("board"),
                    )
                )
            count += 1
        await self._session.flush()
        return count

    async def upsert_daily_bars(self, code: str, bars: Sequence[dict]) -> int:
        count = 0
        for bar in bars:
            trade_date = bar.get("date") or bar.get("trade_date")
            if not trade_date:
                continue
            if isinstance(trade_date, str):
                trade_date = date.fromisoformat(trade_date[:10])
            row = await self._session.get(MarketDailyBar, {"code": code, "trade_date": trade_date})
            values = {
                "open": bar.get("open"),
                "high": bar.get("high"),
                "low": bar.get("low"),
                "close": bar.get("close"),
                "volume": bar.get("volume"),
                "amount": bar.get("amount"),
            }
            if row:
                for k, v in values.items():
                    setattr(row, k, v)
            else:
                self._session.add(
                    MarketDailyBar(code=code, trade_date=trade_date, **values)
                )
            count += 1
        await self._session.flush()
        return count


class SystemJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job: SystemJob) -> SystemJob:
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: str) -> Optional[SystemJob]:
        return await self._session.get(SystemJob, job_id)

    async def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[Decimal] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        values: dict = {}
        if status is not None:
            values["status"] = status
        if progress is not None:
            values["progress"] = progress
        if result is not None:
            values["result"] = result
        if error is not None:
            values["error"] = error
        if values:
            await self._session.execute(
                update(SystemJob).where(SystemJob.id == job_id).values(**values)
            )
